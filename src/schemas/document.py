from pydantic import BaseModel

class ParsedDocument(BaseModel):
    raw_text: str
    source_format: str
    page_count: int
    extraction_method: str
