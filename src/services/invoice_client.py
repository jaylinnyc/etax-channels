"""Client for invoice generation service."""
import httpx
import asyncio
from typing import Tuple, Dict, Any, Optional
import structlog

from src.models.invoice import Invoice
from src.config import settings

logger = structlog.get_logger()


class BaseServiceClient:
    """Base client providing common headers and authentication."""
    
    def __init__(self):
        # We use settings.internal_api_key (ensure this is in your src/config.py)
        # mapped from the INTERNAL_API_KEY env var.
        self.api_key = getattr(settings, "internal_api_key", None)
        logger.info("api_key_loaded", api_key=self.api_key)
        
    @property
    def auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for internal service calls."""
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if self.api_key:
            # Matches the Bearer logic in your Spring Boot SecurityConfig
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class SettingsServiceClient(BaseServiceClient):
    """Client for fetching company settings from the settings API."""
    
    def __init__(self):
        super().__init__()
        self.service_url = settings.settings_service_url
        self.timeout = httpx.Timeout(10.0, connect=5.0)
    
    async def get_company_settings(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Fetch company settings from the settings API."""
        logger.info("fetching_company_settings", service_url=self.service_url)
        
        try:
            headers = self.auth_headers
            logger.info("request_headers", headers={k: v if k != "Authorization" else f"Bearer {v.split()[-1][:10]}..." for k, v in headers.items()})
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.service_url,
                    headers=headers
                )
                
                logger.info("raw_response_preview", content=response.text[:200])
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info("company_settings_fetched_successfully")
                    return True, data
                else:
                    logger.error(
                        "failed_to_fetch_settings",
                        status_code=response.status_code,
                        response=response.text
                    )
                    return False, None
                    
        except Exception as e:
            logger.error("settings_fetch_error", error=str(e))
            return False, None
    
    def extract_company_info(self, settings_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract company information from settings response."""
        try:
            # Matches your Spring Boot response structure: { "settings": { "COMPANY": [...] } }
            company_settings = settings_data.get("settings", {}).get("COMPANY", [])
            
            company_dict = {item["key"]: item["value"] for item in company_settings}
            
            company_info = {
                "tax_id": company_dict.get("company.taxId", ""),
                "name": company_dict.get("company.name", ""),
                "address": company_dict.get("company.address", ""),
                "branch_code": company_dict.get("company.branchCode", "00000"),
                "postal_code": company_dict.get("company.postalCode", "10000"),  # Default to Bangkok if not set
            }
            
            if not all([company_info["tax_id"], company_info["name"], company_info["address"]]):
                logger.warning("missing_required_company_fields", company_info=company_info)
                return None
            
            logger.info("company_info_extracted", company_info=company_info)
            return company_info
            
        except Exception as e:
            logger.error("company_info_extraction_error", error=str(e))
            return None


class InvoiceServiceClient(BaseServiceClient):
    """Client for calling the signing service document creation API."""
    
    def __init__(self):
        super().__init__()
        # Base URL for signing service
        self.base_url = settings.invoice_service_url.split('/api')[0]
        self.create_document_url = f"{self.base_url}/api/v1/documents/create"
        self.sign_document_url = f"{self.base_url}/api/v1/sign"
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.max_retries = 3
    
    async def create_document(self, invoice: Invoice) -> Tuple[bool, Dict[str, Any]]:
        """Create a signed document via the signing service /documents/create endpoint.
        
        This endpoint:
        1. Validates the invoice data
        2. Generates UN/CEFACT XML
        3. Creates a document record
        4. Returns document details
        
        Returns:
            Tuple of (success: bool, response: dict)
        """
        logger.info(
            "document_creation_started",
            url=self.create_document_url,
            seller_tax_id=invoice.seller.tax_id,
            buyer_tax_id=invoice.buyer.tax_id
        )
        
        payload = invoice.to_service_format()
        logger.info("payload_preview", payload_keys=list(payload.keys()))
        
        last_error = None
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(
                        self.create_document_url,
                        json=payload,
                        headers=self.auth_headers
                    )
                    
                    logger.info(
                        "document_service_response",
                        status_code=response.status_code,
                        attempt=attempt
                    )
                    
                    if response.status_code in (200, 201):
                        result = response.json()
                        logger.info("document_created_successfully", document_id=result.get("documentId"))
                        return True, result
                    
                    elif response.status_code in (400, 401, 403, 422):
                        # Client errors - don't retry
                        try:
                            error_data = response.json()
                        except:
                            error_data = {"error": response.text}
                        
                        logger.error("document_creation_client_error", 
                                   status_code=response.status_code, 
                                   error=error_data)
                        return False, error_data
                    
                    else:
                        # Server error - retry
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning("document_service_error", 
                                     status_code=response.status_code,
                                     attempt=attempt)
                        if attempt < self.max_retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
            
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    last_error = str(e)
                    logger.warning("document_service_connection_error", 
                                 attempt=attempt, 
                                 error=last_error)
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                
                except Exception as e:
                    last_error = f"Unexpected error: {str(e)}"
                    logger.error("document_service_unexpected_error", 
                               attempt=attempt, 
                               error=last_error)
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
        
        return False, {"error": last_error or "Max retries reached"}
    
    async def sign_document(self, document_id: str, invoice_number: str, xml_content: str, batch_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Sign a document via the signing service /api/v1/sign endpoint.
        
        This endpoint (SigningController):
        1. Accepts SigningRequest with batchId and documents array
        2. Validates PKCS#11 token connection
        3. Signs the document XML with XAdES-BES
        4. Generates signed PDF with embedded XML
        5. Updates document status to SIGNED
        
        Args:
            document_id: The document UUID
            invoice_number: The invoice/document number
            xml_content: The original XML content
            batch_id: The batch ID from create response
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        logger.info(
            "document_signing_started",
            url=self.sign_document_url,
            document_id=document_id,
            batch_id=batch_id
        )
        
        # Prepare the signing request matching SigningRequest structure
        payload = {
            "batchId": batch_id,
            "documents": [
                {
                    "documentId": document_id,
                    "invoiceNumber": invoice_number,
                    "xmlContent": xml_content
                }
            ],
            "callbackUrl": "internal://bot",
            "submitToRd": False
        }
        
        last_error = None
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(
                        self.sign_document_url,
                        json=payload,
                        headers=self.auth_headers
                    )
                    
                    logger.info(
                        "signing_service_response",
                        status_code=response.status_code,
                        attempt=attempt
                    )
                    
                    if response.status_code in (200, 201):
                        result = response.json()
                        logger.info("document_signed_successfully", document_id=document_id, response=result)
                        return True, result
                    
                    elif response.status_code in (400, 401, 403, 422):
                        # Client errors - don't retry
                        try:
                            error_data = response.json()
                        except:
                            error_data = {"error": response.text}
                        
                        logger.error("document_signing_client_error", 
                                   status_code=response.status_code, 
                                   error=error_data)
                        return False, error_data
                    
                    else:
                        # Server error - retry
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning("signing_service_error", 
                                     status_code=response.status_code,
                                     attempt=attempt)
                        if attempt < self.max_retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
            
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    last_error = str(e)
                    logger.warning("signing_service_connection_error", 
                                 attempt=attempt, 
                                 error=last_error)
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                
                except Exception as e:
                    last_error = f"Unexpected error: {str(e)}"
                    logger.error("signing_service_unexpected_error", 
                               attempt=attempt, 
                               error=last_error)
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
        
        return False, {"error": last_error or "Max retries reached"}
    
    async def download_pdf(self, document_id: str) -> Tuple[bool, bytes]:
        """Download PDF for a document.
        
        Args:
            document_id: The document UUID
            
        Returns:
            Tuple of (success: bool, pdf_bytes: bytes)
        """
        download_url = f"{self.base_url}/api/v1/documents/{document_id}/download"
        
        logger.info("downloading_pdf", document_id=document_id, url=download_url)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    download_url,
                    params={"format": "pdf"},
                    headers=self.auth_headers
                )
                
                if response.status_code == 200:
                    logger.info("pdf_downloaded_successfully", 
                               document_id=document_id,
                               size_bytes=len(response.content))
                    return True, response.content
                else:
                    logger.error("pdf_download_failed",
                               document_id=document_id,
                               status_code=response.status_code)
                    return False, b""
                    
        except Exception as e:
            logger.error("pdf_download_error", document_id=document_id, error=str(e))
            return False, b""
    
    # Keep old method for backward compatibility
    async def generate_invoice(self, invoice: Invoice) -> Tuple[bool, Dict[str, Any]]:
        """Generate and sign an invoice.
        
        This method:
        1. Creates the document (XML generation)
        2. Signs the document (XAdES-BES + PDF with embedded XML)
        
        Returns:
            Tuple of (success: bool, response: dict with both create and sign results)
        """
        # Step 1: Create the document
        create_success, create_response = await self.create_document(invoice)
        
        if not create_success:
            logger.error("document_creation_failed", error=create_response)
            return False, {
                "error": "Failed to create document",
                "details": create_response
            }
        
        # Extract required fields from create response
        document_id = create_response.get("document")  # UUID
        invoice_number = create_response.get("documentNumber")
        xml_content = create_response.get("documentOriginalXml")
        batch_id = create_response.get("batchId")
        
        if not document_id:
            logger.error("document_id_missing_in_response", response=create_response)
            return False, {
                "error": "Document ID not found in creation response",
                "details": create_response
            }
        
        if not invoice_number:
            logger.error("invoice_number_missing_in_response", response=create_response)
            return False, {
                "error": "Invoice number not found in creation response",
                "details": create_response
            }
        
        if not xml_content:
            logger.error("xml_content_missing_in_response", response=create_response)
            return False, {
                "error": "XML content not found in creation response",
                "details": create_response
            }
        
        if not batch_id:
            logger.error("batch_id_missing_in_response", response=create_response)
            return False, {
                "error": "Batch ID not found in creation response",
                "details": create_response
            }
        
        logger.info("document_created_proceeding_to_sign", 
                   document_id=document_id,
                   invoice_number=invoice_number,
                   batch_id=batch_id)
        
        # Step 2: Sign the document
        sign_success, sign_response = await self.sign_document(
            document_id, invoice_number, xml_content, batch_id
        )
        
        if not sign_success:
            logger.error("document_signing_failed", document_id=document_id, error=sign_response)
            return False, {
                "error": "Failed to sign document",
                "document_id": document_id,
                "invoice_number": invoice_number,
                "details": sign_response
            }
        
        # Success - return combined response
        logger.info("invoice_generated_and_signed_successfully", document_id=document_id)
        return True, {
            "message": "Invoice created and signed successfully",
            "document_id": document_id,
            "invoice_number": invoice_number,
            "create_response": create_response,
            "sign_response": sign_response
        }

    async def health_check(self) -> bool:
        """Check if the invoice service is available via Actuator."""
        try:
            # Use actuator/health which we permitted in SecurityConfig
            health_url = self.service_url.split('/api')[0] + '/actuator/health'
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(health_url)
                return response.status_code == 200
        except Exception as e:
            logger.warning("invoice_service_health_check_failed", error=str(e))
            return False


# Global service client instances
settings_service = SettingsServiceClient()
invoice_service = InvoiceServiceClient()