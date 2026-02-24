"""Client for invoice generation service."""
import httpx
from typing import Tuple, Dict, Any
import structlog

from src.models.invoice import Invoice
from src.config import settings

logger = structlog.get_logger()


class InvoiceServiceClient:
    """Client for calling the invoice generation microservice."""
    
    def __init__(self):
        """Initialize the service client."""
        self.service_url = settings.invoice_service_url
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.max_retries = 3
    
    async def generate_invoice(self, invoice: Invoice) -> Tuple[bool, Dict[str, Any]]:
        """Generate invoice by calling the external service.
        
        Args:
            invoice: Invoice data to send
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        logger.info(
            "invoice_generation_started",
            service_url=self.service_url,
            seller_tax_id=invoice.seller.tax_id,
            buyer_tax_id=invoice.buyer.tax_id
        )
        
        # Convert invoice to service format
        payload = invoice.to_service_format()
        
        # Retry logic
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.service_url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        }
                    )
                    
                    # Log response
                    logger.info(
                        "invoice_service_response",
                        status_code=response.status_code,
                        attempt=attempt
                    )
                    
                    # Check for success
                    if response.status_code in (200, 201):
                        try:
                            response_data = response.json()
                        except Exception:
                            response_data = {"message": "Invoice generated successfully", "raw": response.text}
                        
                        logger.info("invoice_generated_successfully")
                        return True, response_data
                    
                    elif response.status_code in (400, 422):
                        # Client error - don't retry
                        try:
                            error_data = response.json()
                        except Exception:
                            error_data = {"error": response.text}
                        
                        logger.error(
                            "invoice_validation_error",
                            status_code=response.status_code,
                            error=error_data
                        )
                        return False, {"error": f"Validation error: {error_data}"}
                    
                    else:
                        # Server error - retry
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning(
                            "invoice_service_error",
                            status_code=response.status_code,
                            attempt=attempt,
                            max_attempts=self.max_retries
                        )
                        
                        if attempt < self.max_retries:
                            # Exponential backoff
                            await httpx.AsyncClient().aclose()
                            import asyncio
                            await asyncio.sleep(2 ** attempt)
                            continue
            
            except httpx.TimeoutException as e:
                last_error = f"Request timeout: {str(e)}"
                logger.warning(
                    "invoice_service_timeout",
                    attempt=attempt,
                    max_attempts=self.max_retries,
                    error=str(e)
                )
                
                if attempt < self.max_retries:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
            
            except httpx.ConnectError as e:
                last_error = f"Connection error: {str(e)}"
                logger.error(
                    "invoice_service_connection_error",
                    attempt=attempt,
                    max_attempts=self.max_retries,
                    error=str(e)
                )
                
                if attempt < self.max_retries:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
            
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(
                    "invoice_service_unexpected_error",
                    attempt=attempt,
                    error=str(e)
                )
                
                if attempt < self.max_retries:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
        
        # All retries failed
        logger.error(
            "invoice_generation_failed",
            max_attempts=self.max_retries,
            last_error=last_error
        )
        return False, {"error": last_error or "Unknown error occurred"}
    
    async def health_check(self) -> bool:
        """Check if the invoice service is available.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                # Try a HEAD or GET request to check connectivity
                response = await client.get(self.service_url.rsplit('/', 1)[0] + '/health', 
                                           follow_redirects=True)
                return response.status_code < 500
        except Exception as e:
            logger.warning("invoice_service_health_check_failed", error=str(e))
            return False


# Global service client instance
invoice_service = InvoiceServiceClient()
