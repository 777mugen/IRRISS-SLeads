---
title: Deep Research for Refactoring Plan - Best Practices & Implementation Details
type: research
date: 2026-03-12
related_plan: docs/plans/2026-03-12-refactor-data-source-and-extraction-plan.md
---

# Deep Research: Best Practices for SLeads Refactoring

This document provides comprehensive research findings for the 5 critical sections of the refactoring plan, including official documentation, code examples, common pitfalls, and optimization strategies.

---

## Section 1: Database Migration - PostgreSQL Best Practices

### 1.1 Official Documentation URLs

- **PostgreSQL Documentation**: https://www.postgresql.org/docs/current/index.html
- **Alembic Migration Guide**: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- **PostgreSQL Index Types**: https://www.postgresql.org/docs/current/indexes-types.html
- **TRUNCATE Command**: https://www.postgresql.org/docs/current/sql-truncate.html
- **Foreign Keys & Cascading**: https://www.postgresql.org/docs/current/ddl-constraints.html

### 1.2 Best Practices for Production Database Migrations

#### Safe Migration Pattern

```python
# alembic/versions/xxx_refactor_data_source.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # 1. BACKUP FIRST (manual step - document this!)
    # pg_dump -U username -d dbname > backup_$(date +%Y%m%d_%H%M%S).sql
    
    # 2. Create new tables BEFORE dropping old data
    op.create_table(
        'raw_markdown',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doi', sa.String(), nullable=False),
        sa.Column('pmid', sa.String(), nullable=True),
        sa.Column('markdown_content', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=False),
        sa.Column('fetched_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doi', name='uq_raw_markdown_doi')
    )
    
    # 3. Add new columns to existing tables (non-destructive)
    op.add_column('paper_leads', sa.Column('source', sa.String(50), server_default='PubMed'))
    op.add_column('paper_leads', sa.Column('article_url', sa.String()))
    
    # 4. Add unique constraint separately (allows NULL values)
    op.create_unique_constraint('uq_paper_leads_doi', 'paper_leads', ['doi'])
    
    # 5. Create indexes AFTER data operations
    op.create_index('idx_raw_markdown_doi', 'raw_markdown', ['doi'])
    op.create_index('idx_paper_leads_source', 'paper_leads', ['source'])
    
    # 6. Create feedback table with proper foreign key
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('paper_lead_id', sa.Integer(), nullable=True),
        sa.Column('accuracy', sa.String(10), nullable=True),
        sa.Column('demand_match', sa.String(10), nullable=True),
        sa.Column('contact_validity', sa.String(10), nullable=True),
        sa.Column('deal_speed', sa.String(10), nullable=True),
        sa.Column('deal_price', sa.String(10), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['paper_lead_id'], ['paper_leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_feedback_paper_lead_id', 'feedback', ['paper_lead_id'])
    
    # 7. ONLY THEN truncate old data
    op.execute("TRUNCATE TABLE paper_leads CASCADE")
    op.execute("TRUNCATE TABLE tender_leads CASCADE")
    op.execute("TRUNCATE TABLE crawled_urls CASCADE")
    
    # 8. Drop deprecated columns
    op.drop_column('paper_leads', 'keywords_matched')

def downgrade():
    # Reverse operations in opposite order
    op.add_column('paper_leads', sa.Column('keywords_matched', sa.Text()))
    op.drop_index('idx_feedback_paper_lead_id')
    op.drop_table('feedback')
    op.drop_index('idx_paper_leads_source')
    op.drop_index('idx_raw_markdown_doi')
    op.drop_constraint('uq_paper_leads_doi', 'paper_leads', type_='unique')
    op.drop_column('paper_leads', 'article_url')
    op.drop_column('paper_leads', 'source')
    op.drop_table('raw_markdown')
```

#### Key Safety Measures

1. **Always backup before migration**
2. **Create new tables before dropping old data**
3. **Use transactions (Alembic does this by default)**
4. **Test migration on staging environment first**
5. **Have rollback plan ready**

### 1.3 Safest Way to Add New Tables

#### Non-Locking Pattern

```python
# Create table without blocking reads
op.create_table(
    'raw_markdown',
    # ... columns ...
)

# PostgreSQL CREATE TABLE doesn't lock other tables
# Safe to run on production
```

#### Partial Indexes for Performance

```sql
-- Create partial index for common query patterns
CREATE INDEX idx_raw_markdown_fetched_recent 
ON raw_markdown(fetched_at) 
WHERE fetched_at > NOW() - INTERVAL '30 days';

-- This index only includes recent records, saving space
```

### 1.4 Index Optimization for DOI Lookups

#### DOI Index Strategy

```sql
-- Primary lookup index (B-tree for exact matches)
CREATE UNIQUE INDEX idx_raw_markdown_doi ON raw_markdown(doi);

-- Covering index for common queries (include frequently accessed columns)
CREATE INDEX idx_raw_markdown_doi_covering 
ON raw_markdown(doi) 
INCLUDE (pmid, source_url, fetched_at);

-- Text pattern ops for prefix searches (if needed)
CREATE INDEX idx_raw_markdown_doi_prefix 
ON raw_markdown(doi text_pattern_ops);

-- Hash index for equality-only lookups (faster than B-tree for =)
CREATE INDEX idx_raw_markdown_doi_hash ON raw_markdown USING HASH (doi);
```

#### Index Performance Tips

1. **Use UNIQUE constraint for DOI** (enforces data integrity + creates index)
2. **Consider HASH indexes for DOI equality lookups** (faster but no range queries)
3. **Use INCLUDE clause** for covering indexes (avoids table lookups)
4. **Avoid over-indexing** (indexes slow down INSERTs)
5. **Partial indexes** for time-based queries

### 1.5 Common Gotchas & Pitfalls

#### 1. NULL in UNIQUE Constraints

```sql
-- ❌ WRONG: Multiple NULL DOIs allowed by default
CREATE TABLE bad_example (
    doi VARCHAR UNIQUE,
    pmid VARCHAR
);

-- ✅ CORRECT: Use COALESCE for proper uniqueness
CREATE TABLE good_example (
    doi VARCHAR,
    pmid VARCHAR,
    CONSTRAINT unique_doi_or_pmid UNIQUE (COALESCE(doi, pmid))
);

-- Or use filtered unique index
CREATE UNIQUE INDEX uq_doi_not_null ON paper_leads(doi) WHERE doi IS NOT NULL;
```

#### 2. TRUNCATE vs DELETE

```sql
-- TRUNCATE is faster but:
-- ❌ Cannot be rolled back (in some PostgreSQL versions)
-- ❌ Doesn't fire triggers
-- ❌ Requires CASCADE for foreign keys

-- ✅ Use TRUNCATE for development/migrations
TRUNCATE TABLE paper_leads CASCADE;

-- ✅ Use DELETE for production data retention
DELETE FROM paper_leads WHERE created_at < '2026-01-01';
```

#### 3. Foreign Key CASCADE Behavior

```sql
-- ❌ DANGEROUS: Can delete lots of data unintentionally
CREATE TABLE feedback (
    paper_lead_id INTEGER REFERENCES paper_leads(id) ON DELETE CASCADE
);

-- ✅ SAFER: Restrict deletion if feedback exists
CREATE TABLE feedback (
    paper_lead_id INTEGER REFERENCES paper_leads(id) ON DELETE RESTRICT
);

-- Or set NULL to preserve feedback
CREATE TABLE feedback (
    paper_lead_id INTEGER REFERENCES paper_leads(id) ON DELETE SET NULL
);
```

### 1.6 Performance Optimization Tips

#### Connection Pooling

```python
# src/db/connection.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # Number of connections to keep
    max_overflow=20,        # Additional connections when pool exhausted
    pool_pre_ping=True,     # Check connection health before use
    pool_recycle=3600,      # Recycle connections after 1 hour
)
```

#### Batch Inserts

```python
# ❌ SLOW: Individual inserts
for markdown in markdowns:
    await db.execute(
        "INSERT INTO raw_markdown (doi, markdown_content, source_url) VALUES ($1, $2, $3)",
        [markdown.doi, markdown.content, markdown.url]
    )

# ✅ FAST: Batch insert
await db.execute_many(
    "INSERT INTO raw_markdown (doi, markdown_content, source_url) VALUES ($1, $2, $3)",
    [(m.doi, m.content, m.url) for m in markdowns]
)
```

---

## Section 2: PubMed Entrez API

### 2.1 Official Documentation URLs

- **Entrez Programming Utilities**: https://www.ncbi.nlm.nih.gov/books/NBK25500/
- **E-utilities Quick Start**: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- **E-utilities Reference**: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- **API Key Information**: https://www.ncbi.nlm.nih.gov/books/NBK25497/
- **Usage Guidelines**: https://www.ncbi.nlm.nih.gov/home/about/policies/

### 2.2 Rate Limits and Error Handling

#### Official Rate Limits

```python
# src/crawlers/pubmed_entrez.py
"""
Official Rate Limits (as of 2026):
- Without API key: 3 requests per second
- With API key: 10 requests per second
- Large requests: May be throttled during peak hours

Best Practices:
1. Always provide email and tool name
2. Get API key for higher limits
3. Implement exponential backoff
4. Cache results when possible
"""

import asyncio
from datetime import datetime
import httpx

class RateLimiter:
    def __init__(self, requests_per_second: int = 3):
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0.0
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            wait_time = self.last_request + self.min_interval - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.last_request = time.time()

class PubMedEntrezClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(
        self, 
        email: str = "Shane@irriss.com",
        tool: str = "IRRISS-SLeads",
        api_key: str = None
    ):
        self.email = email
        self.tool = tool
        self.api_key = api_key
        
        # Rate limiter: 3 req/s without key, 10 req/s with key
        rate = 10 if api_key else 3
        self.rate_limiter = RateLimiter(rate)
        
        self.http = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5)
        )
    
    async def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make rate-limited request with retry logic"""
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            await self.rate_limiter.acquire()
            
            # Add required parameters
            params.update({
                "email": self.email,
                "tool": self.tool,
                "retmode": "json"
            })
            
            if self.api_key:
                params["api_key"] = self.api_key
            
            try:
                response = await self.http.get(
                    f"{self.BASE_URL}/{endpoint}",
                    params=params
                )
                
                # Check for rate limit
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    # Server error, retry with exponential backoff
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                raise
                
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                raise
        
        raise Exception(f"Failed after {max_retries} retries")
```

### 2.3 Best Practices for Batch PMID Searches

#### Efficient Batch Pattern

```python
async def search_batch(
    self,
    query: str,
    max_results: int = 100,
    batch_size: int = 20,
    date_range: tuple = None
) -> List[str]:
    """
    Search PubMed in batches to handle large result sets
    
    Strategy:
    1. First request gets total count
    2. Subsequent requests fetch in batches
    3. Use retstart/retmax for pagination
    """
    # First request: get count
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": 0,  # Just get count
    }
    
    if date_range:
        start_year, end_year = date_range
        params["datetype"] = "pdat"
        params["mindate"] = f"{start_year}/01/01"
        params["maxdate"] = f"{end_year}/12/31"
    
    data = await self._make_request("esearch.fcgi", params)
    total_count = int(data["esearchresult"]["count"])
    
    print(f"Found {total_count} results for query: {query}")
    
    # Fetch PMIDs in batches
    all_pmids = []
    for start in range(0, min(total_count, max_results), batch_size):
        params["retstart"] = start
        params["retmax"] = min(batch_size, max_results - start)
        
        data = await self._make_request("esearch.fcgi", params)
        pmids = data["esearchresult"]["idlist"]
        all_pmids.extend(pmids)
        
        print(f"Fetched {len(all_pmids)}/{min(total_count, max_results)} PMIDs")
    
    return all_pmids

async def fetch_details_batch(
    self,
    pmids: List[str],
    batch_size: int = 200
) -> List[dict]:
    """
    Fetch paper details in batches
    
    Official API allows up to 200 PMIDs per request
    """
    results = []
    
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml"
        }
        
        data = await self._make_request("efetch.fcgi", params)
        
        # Parse XML to extract DOI, title, authors, etc.
        parsed = self._parse_pubmed_xml(data)
        results.extend(parsed)
    
    return results
```

### 2.4 Handling "No Results" Scenarios

```python
async def search_with_fallback(self, query: str) -> List[str]:
    """
    Search with multiple fallback strategies
    """
    # Try 1: Original query
    pmids = await self.search(query)
    if pmids:
        return pmids
    
    # Try 2: Simplified query (remove complex terms)
    simplified = self._simplify_query(query)
    pmids = await self.search(simplified)
    if pmids:
        return pmids
    
    # Try 3: Remove date restrictions
    pmids = await self.search(query, date_range=None)
    if pmids:
        return pmids
    
    # Try 4: Use OR operator for synonyms
    expanded = self._expand_synonyms(query)
    pmids = await self.search(expanded)
    if pmids:
        return pmids
    
    # No results found
    logger.warning(f"No results found for query: {query}")
    return []

def _simplify_query(self, query: str) -> str:
    """Remove complex boolean operators"""
    # Remove [Field] qualifiers
    simplified = re.sub(r'\[.*?\]', '', query)
    # Remove OR/AND/NOT
    simplified = re.sub(r'\b(OR|AND|NOT)\b', ' ', simplified)
    return simplified.strip()

def _expand_synonyms(self, query: str) -> str:
    """Add common synonyms using OR"""
    synonyms = {
        "Multiplex Immunofluorescence": 
            "Multiplex Immunofluorescence OR mIF OR multiplex IF",
        "Cancer": 
            "Cancer OR tumor OR neoplasm OR carcinoma",
    }
    
    for term, expansion in synonyms.items():
        if term.lower() in query.lower():
            query = query.replace(term, expansion)
    
    return query
```

### 2.5 Common Gotchas & Pitfalls

#### 1. Missing Email/Tool Parameters

```python
# ❌ WRONG: Missing required parameters (may get blocked)
response = await http.get(f"{BASE_URL}/esearch.fcgi?db=pubmed&term=cancer")

# ✅ CORRECT: Always include email and tool
params = {
    "db": "pubmed",
    "term": "cancer",
    "email": "your@email.com",
    "tool": "YourAppName"
}
```

#### 2. Incorrect Date Format

```python
# ❌ WRONG: Wrong date format
params["mindate"] = "2026-01-01"  # Should be YYYY/MM/DD

# ✅ CORRECT: Use proper format
params["mindate"] = "2026/01/01"
params["maxdate"] = "2026/12/31"
```

#### 3. Not Handling Empty Results

```python
# ❌ WRONG: Assumes results exist
data = await search(query)
pmids = data["esearchresult"]["idlist"]  # May not exist

# ✅ CORRECT: Handle missing data
data = await search(query)
pmids = data.get("esearchresult", {}).get("idlist", [])
```

### 2.6 Performance Optimization Tips

#### 1. Use ESummary Instead of EFetch for Basic Info

```python
# ESummary is faster than EFetch when you only need basic info
async def get_basic_info(self, pmids: List[str]) -> List[dict]:
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json"
    }
    
    data = await self._make_request("esummary.fcgi", params)
    
    # Returns: {uid: {title, authors, pubdate, ...}}
    return data.get("result", {})
```

#### 2. Use ELink for Related Articles

```python
async def get_related_articles(self, pmid: str) -> List[str]:
    """Get related articles using ELink"""
    params = {
        "dbfrom": "pubmed",
        "db": "pubmed",
        "id": pmid,
        "cmd": "neighbor"
    }
    
    data = await self._make_request("elink.fcgi", params)
    # Parse link sets to get related PMIDs
    related = []
    for linkset in data.get("linksets", []):
        for linksetdb in linkset.get("linksetdbs", []):
            related.extend(linksetdb.get("links", []))
    
    return related
```

#### 3. Cache Common Queries

```python
from datetime import timedelta
import hashlib

class CachedPubMedClient(PubMedEntrezClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}  # Use Redis in production
        self.cache_ttl = timedelta(hours=24)
    
    async def search(self, query: str, **kwargs) -> List[str]:
        # Create cache key
        cache_key = hashlib.md5(
            f"{query}:{kwargs}".encode()
        ).hexdigest()
        
        # Check cache
        if cache_key in self.cache:
            cached, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return cached
        
        # Fetch and cache
        results = await super().search(query, **kwargs)
        self.cache[cache_key] = (results, datetime.now())
        
        return results
```

---

## Section 3: NCBI ID Converter API

### 3.1 Official Documentation URLs

- **ID Converter API**: https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
- **PMC ID Conversion**: https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter/
- **API Terms of Use**: https://www.ncbi.nlm.nih.gov/home/about/policies/

### 3.2 API Documentation & Usage

#### Official API Endpoint

```python
# src/crawlers/ncbi_id_converter.py
"""
NCBI ID Converter API

Endpoint: https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/

Supported IDs:
- PMID (PubMed ID)
- PMCID (PubMed Central ID)
- DOI (Digital Object Identifier)
- NIHMSID (NIH Manuscript Submission ID)

Rate Limits:
- No official limit stated, but be respectful
- Recommend: 1 request per second
- Batch up to 200 IDs per request
"""

import httpx
from typing import Dict, List, Optional
import asyncio

class NCBIIDConverter:
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self.rate_limiter = RateLimiter(1)  # 1 req/s
    
    async def convert_pmids_to_dois(
        self,
        pmids: List[str],
        batch_size: int = 100
    ) -> Dict[str, Optional[str]]:
        """
        Convert PMIDs to DOIs
        
        Returns: {pmid: doi, ...} (doi may be None)
        """
        results = {}
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            await self.rate_limiter.acquire()
            
            params = {
                "ids": ",".join(batch),
                "format": "json",
                "tool": "IRRISS-SLeads",
                "email": "Shane@irriss.com"
            }
            
            try:
                response = await self.http.get(self.BASE_URL, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                for record in data.get("records", []):
                    pmid = record.get("pmid")
                    doi = record.get("doi")
                    
                    # Handle different statuses
                    status = record.get("status")
                    
                    if status == "error":
                        # Invalid PMID or conversion failed
                        results[pmid] = None
                        logger.warning(f"PMID {pmid} conversion failed: {record}")
                    else:
                        results[pmid] = doi
                
            except Exception as e:
                logger.error(f"Batch conversion failed: {e}")
                # Mark all PMIDs in batch as failed
                for pmid in batch:
                    results[pmid] = None
        
        return results
```

### 3.3 Error Handling When DOI Unavailable

```python
from dataclasses import dataclass
from enum import Enum

class ConversionStatus(Enum):
    SUCCESS = "success"
    NO_DOI = "no_doi"
    INVALID_ID = "invalid_id"
    ERROR = "error"

@dataclass
class ConversionResult:
    pmid: str
    doi: Optional[str]
    status: ConversionStatus
    pmcid: Optional[str] = None
    error_message: Optional[str] = None

async def convert_with_detailed_status(
    self,
    pmids: List[str]
) -> List[ConversionResult]:
    """
    Convert PMIDs with detailed status reporting
    """
    results = []
    
    params = {
        "ids": ",".join(pmids),
        "format": "json"
    }
    
    await self.rate_limiter.acquire()
    response = await self.http.get(self.BASE_URL, params=params)
    data = response.json()
    
    for record in data.get("records", []):
        pmid = record.get("pmid")
        doi = record.get("doi")
        pmcid = record.get("pmcid")
        status = record.get("status")
        
        if status == "error":
            results.append(ConversionResult(
                pmid=pmid,
                doi=None,
                status=ConversionStatus.ERROR,
                error_message=record.get("errmsg", "Unknown error")
            ))
        elif not doi:
            results.append(ConversionResult(
                pmid=pmid,
                doi=None,
                status=ConversionStatus.NO_DOI,
                pmcid=pmcid
            ))
        else:
            results.append(ConversionResult(
                pmid=pmid,
                doi=doi,
                status=ConversionStatus.SUCCESS,
                pmcid=pmcid
            ))
    
    return results

# Usage example
async def handle_missing_dois(pmids: List[str]):
    """
    Strategy for handling PMIDs without DOIs
    """
    converter = NCBIIDConverter()
    results = await converter.convert_with_detailed_status(pmids)
    
    papers_with_doi = []
    papers_without_doi = []
    
    for result in results:
        if result.status == ConversionStatus.SUCCESS:
            papers_with_doi.append({
                "pmid": result.pmid,
                "doi": result.doi
            })
        elif result.status == ConversionStatus.NO_DOI:
            # Use PMCID or PMID as identifier
            papers_without_doi.append({
                "pmid": result.pmid,
                "pmcid": result.pmcid,
                "doi": None,
                "article_url": f"https://pubmed.ncbi.nlm.nih.gov/{result.pmid}/"
            })
        else:
            # Log errors
            logger.error(f"Failed to convert {result.pmid}: {result.error_message}")
    
    return papers_with_doi, papers_without_doi
```

### 3.4 Batch Conversion Limits

```python
"""
Official Batch Limits:
- Maximum IDs per request: No hard limit, but recommended < 200
- Request frequency: No official limit, use 1/second
- Response size: May timeout with very large batches

Best Practices:
1. Batch size: 100-200 IDs
2. Rate limit: 1 request per second
3. Timeout: 30 seconds
4. Retry: 3 attempts with exponential backoff
"""

async def batch_convert_safely(
    self,
    pmids: List[str],
    batch_size: int = 100,
    max_retries: int = 3
) -> Dict[str, Optional[str]]:
    """
    Safely convert large batches of PMIDs
    """
    all_results = {}
    
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        
        for attempt in range(max_retries):
            try:
                results = await self.convert_pmids_to_dois(batch)
                all_results.update(results)
                break
                
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    # Reduce batch size and retry
                    batch_size = batch_size // 2
                    logger.warning(f"Timeout, reducing batch size to {batch_size}")
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"Batch failed after {max_retries} retries")
                    # Mark all as failed
                    for pmid in batch:
                        all_results[pmid] = None
        
        # Progress tracking
        logger.info(f"Converted {len(all_results)}/{len(pmids)} PMIDs")
    
    return all_results
```

### 3.5 Common Gotchas & Pitfalls

#### 1. Different ID Formats

```python
# ❌ WRONG: Mixed ID formats
params["ids"] = "12345678, PMC1234567, 10.1234/example"

# ✅ CORRECT: Use consistent ID type
params["ids"] = "12345678, 23456789, 34567890"  # All PMIDs

# ✅ CORRECT: Specify ID type if needed
params["ids"] = "PMC1234567, PMC2345678"
params["idtype"] = "pmcid"
```

#### 2. Ignoring Status Field

```python
# ❌ WRONG: Assumes all conversions succeed
for record in data["records"]:
    results[record["pmid"]] = record["doi"]

# ✅ CORRECT: Check status field
for record in data["records"]:
    if record.get("status") == "error":
        logger.warning(f"Conversion failed: {record}")
        results[record["pmid"]] = None
    else:
        results[record["pmid"]] = record.get("doi")
```

### 3.6 Performance Optimization Tips

#### 1. Pre-filter Known DOIs

```python
async def smart_convert(
    self,
    papers: List[dict]  # Each has 'pmid' and possibly 'doi'
) -> Dict[str, str]:
    """
    Only convert PMIDs that don't already have DOIs
    """
    # Separate papers with/without DOI
    papers_without_doi = [
        p for p in papers 
        if not p.get("doi")
    ]
    
    pmids_to_convert = [p["pmid"] for p in papers_without_doi]
    
    # Only convert those without DOI
    conversions = await self.convert_pmids_to_dois(pmids_to_convert)
    
    # Merge results
    all_dois = {p["pmid"]: p.get("doi") for p in papers}
    all_dois.update(conversions)
    
    return all_dois
```

#### 2. Cache Results

```python
import json
from pathlib import Path

class CachedIDConverter(NCBIIDConverter):
    def __init__(self, cache_file: str = "data/doi_cache.json"):
        super().__init__()
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, str]:
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)
    
    async def convert_pmids_to_dois(
        self,
        pmids: List[str]
    ) -> Dict[str, Optional[str]]:
        # Check cache first
        uncached = [p for p in pmids if p not in self.cache]
        
        if uncached:
            # Convert only uncached
            new_results = await super().convert_pmids_to_dois(uncached)
            self.cache.update(new_results)
            self._save_cache()
        
        # Return all from cache
        return {pmid: self.cache.get(pmid) for pmid in pmids}
```

---

## Section 4: Two-Stage Extraction with GLM-5

### 4.1 GLM-5 Context Window Limits

```python
"""
GLM-5 Model Specifications:
- GLM-5-Plus: 128K context window (128,000 tokens)
- GLM-4: 128K context window
- GLM-3-Turbo: 128K context window

Token Estimation:
- English: ~1 token per 4 characters (0.25 tokens/char)
- Chinese: ~1 token per 1.5-2 characters

Safe Limits for Production:
- Reserve 20% for system prompt + response
- Max input: 100K tokens (~400K characters English, ~150K Chinese)
- Typical paper markdown: 10,000-50,000 characters
"""

# src/extractors/token_utils.py
import re

def estimate_tokens(text: str, is_chinese: bool = False) -> int:
    """
    Estimate token count for text
    
    Approximation:
    - English: 0.25 tokens/char
    - Chinese: 0.5-0.67 tokens/char
    """
    if is_chinese:
        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 0.6 + other_chars * 0.25)
    else:
        return int(len(text) * 0.25)

def truncate_to_token_limit(
    text: str,
    max_tokens: int = 100000,
    is_chinese: bool = False
) -> str:
    """
    Truncate text to fit within token limit
    """
    estimated = estimate_tokens(text, is_chinese)
    
    if estimated <= max_tokens:
        return text
    
    # Calculate character limit
    chars_per_token = 4 if not is_chinese else 1.5
    max_chars = int(max_tokens * chars_per_token)
    
    # Truncate with overlap for context preservation
    return text[:max_chars]
```

### 4.2 Best Practices for Multi-Stage LLM Extraction

#### Architecture Pattern

```python
# src/extractors/two_stage_extractor.py
"""
Two-Stage Extraction Pattern

Stage 1: Locate - Find relevant sections in document
Stage 2: Extract - Extract structured data from sections

Benefits:
1. Avoids context overflow by working with smaller chunks
2. Better accuracy (focused extraction)
3. Easier debugging (can inspect each stage)
4. Lower cost (smaller prompts)
"""

from typing import Dict, List, Optional
import json
from dataclasses import dataclass

@dataclass
class LocationInfo:
    """Result from Stage 1: Location"""
    correspondence_start: int
    correspondence_end: int
    affiliation_start: int
    email_line: int
    confidence: float

@dataclass
class ExtractedFields:
    """Result from Stage 2: Extraction"""
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    institution: Optional[str]
    address: Optional[str]
    confidence: float

class TwoStageExtractor:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.max_stage1_tokens = 50000   # For location
        self.max_stage2_tokens = 10000   # For extraction
    
    async def extract(self, markdown: str) -> Dict:
        """
        Main extraction flow
        """
        # Stage 1: Locate relevant sections
        locations = await self._locate_keywords(markdown)
        
        if not locations or locations.confidence < 0.5:
            logger.warning("Stage 1 failed: Could not locate keywords")
            return self._empty_result()
        
        # Stage 2: Extract from located sections
        sections = self._extract_sections(markdown, locations)
        fields = await self._extract_fields(sections)
        
        return {
            "corresponding_author": {
                "name": fields.name,
                "email": fields.email,
                "phone": fields.phone,
                "institution": fields.institution,
                "address": fields.address
            },
            "confidence": fields.confidence,
            "locations": locations.__dict__
        }
    
    async def _locate_keywords(self, markdown: str) -> Optional[LocationInfo]:
        """
        Stage 1: Locate keywords in document
        
        Strategy:
        1. Split markdown into chunks if too long
        2. Use LLM to find keyword positions
        3. Return line numbers
        """
        # Truncate if needed
        truncated = truncate_to_token_limit(
            markdown,
            self.max_stage1_tokens,
            is_chinese=True
        )
        
        lines = truncated.split('\n')
        
        prompt = f"""
Task: Locate the following keywords in this scientific paper and return their line numbers.

Keywords to find:
1. "Correspondence" or "Corresponding Author" or "通讯作者"
2. "Affiliation" or "单位" or "机构"
3. "Email" or "E-mail" or "邮箱" or "电子邮件"

Document (line numbers added):
```
{self._add_line_numbers(lines[:500])}
```

Return JSON format:
{{
  "correspondence_start": <line_number>,
  "correspondence_end": <line_number>,
  "affiliation_start": <line_number>,
  "email_line": <line_number>,
  "confidence": <0.0-1.0>
}}

If a keyword is not found, set its value to null.
Only return the JSON, no explanation.
"""
        
        response = await self.llm.call(
            prompt,
            response_format={"type": "json_object"}
        )
        
        try:
            data = json.loads(response)
            return LocationInfo(
                correspondence_start=data.get("correspondence_start", 0),
                correspondence_end=data.get("correspondence_end", len(lines)),
                affiliation_start=data.get("affiliation_start", 0),
                email_line=data.get("email_line", 0),
                confidence=data.get("confidence", 0.0)
            )
        except Exception as e:
            logger.error(f"Failed to parse location response: {e}")
            return None
    
    def _extract_sections(
        self,
        markdown: str,
        locations: LocationInfo
    ) -> Dict[str, str]:
        """
        Extract relevant sections based on locations
        """
        lines = markdown.split('\n')
        
        # Extract correspondence section (with buffer)
        start = max(0, locations.correspondence_start - 5)
        end = min(len(lines), locations.correspondence_end + 10)
        correspondence = '\n'.join(lines[start:end])
        
        # Extract affiliation section
        if locations.affiliation_start:
            aff_start = max(0, locations.affiliation_start - 2)
            aff_end = min(len(lines), locations.affiliation_start + 20)
            affiliation = '\n'.join(lines[aff_start:aff_end])
        else:
            affiliation = correspondence  # Use correspondence section
        
        return {
            "correspondence": correspondence,
            "affiliation": affiliation
        }
    
    async def _extract_fields(
        self,
        sections: Dict[str, str]
    ) -> ExtractedFields:
        """
        Stage 2: Extract fields from sections
        """
        prompt = f"""
Task: Extract contact information from this scientific paper section.

Text:
```
{sections['correspondence']}
```

Extract the following fields (return null if not found):
{{
  "name": "Corresponding author's full name",
  "email": "Email address",
  "phone": "Phone number (include country code)",
  "institution": "Institution/university name",
  "address": "Full postal address",
  "confidence": <0.0-1.0>
}}

Only return the JSON, no explanation.
"""
        
        response = await self.llm.call(
            prompt,
            response_format={"type": "json_object"}
        )
        
        try:
            data = json.loads(response)
            return ExtractedFields(
                name=data.get("name"),
                email=data.get("email"),
                phone=data.get("phone"),
                institution=data.get("institution"),
                address=data.get("address"),
                confidence=data.get("confidence", 0.0)
            )
        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}")
            return ExtractedFields(None, None, None, None, None, 0.0)
    
    @staticmethod
    def _add_line_numbers(lines: List[str]) -> str:
        """Add line numbers to text"""
        return '\n'.join(
            f"{i+1:4d}: {line}" 
            for i, line in enumerate(lines)
        )
    
    @staticmethod
    def _empty_result() -> Dict:
        """Return empty result structure"""
        return {
            "corresponding_author": {
                "name": None,
                "email": None,
                "phone": None,
                "institution": None,
                "address": None
            },
            "confidence": 0.0
        }
```

### 4.3 Prompt Engineering for Keyword Location

#### Effective Prompts

```python
# ✅ GOOD: Clear, structured, with examples
STAGE1_PROMPT_TEMPLATE = """
Task: Locate keyword positions in a scientific paper.

You will be given a document with line numbers. Find the following keywords:
1. Correspondence / Corresponding Author / 通讯作者
2. Affiliation / 单位 / 机构
3. Email / E-mail / 邮箱

Document:
{document_with_line_numbers}

Instructions:
1. Find the FIRST occurrence of each keyword
2. For multi-line sections (like correspondence), identify start AND end
3. Return the line number where information appears
4. If keyword not found, return null for that field

Return ONLY this JSON structure:
{{
  "correspondence_start": <line_number_or_null>,
  "correspondence_end": <line_number_or_null>,
  "affiliation_start": <line_number_or_null>,
  "email_line": <line_number_or_null>,
  "confidence": <0.0_to_1.0>
}}

Example output:
{{
  "correspondence_start": 42,
  "correspondence_end": 48,
  "affiliation_start": 35,
  "email_line": 45,
  "confidence": 0.95
}}
"""

# ❌ BAD: Vague, no structure
BAD_PROMPT = "Find the author information in this text and tell me where it is."

# ✅ GOOD: Specific, with format requirements
STAGE2_PROMPT_TEMPLATE = """
Task: Extract contact information from a text section.

Section:
{section}

Extract these fields:
- name: Full name of corresponding author (e.g., "John Smith" or "张三")
- email: Email address (e.g., "john.smith@university.edu")
- phone: Phone number with country code (e.g., "+1-555-123-4567")
- institution: University or organization name (e.g., "Harvard University")
- address: Full postal address (e.g., "123 Main St, Cambridge, MA 02139, USA")

Rules:
1. Return null if field is not found
2. Do not make up information
3. Preserve original language (Chinese/English)
4. Include confidence score (0.0-1.0)

Return ONLY JSON:
{{
  "name": <string_or_null>,
  "email": <string_or_null>,
  "phone": <string_or_null>,
  "institution": <string_or_null>,
  "address": <string_or_null>,
  "confidence": <0.0_to_1.0>
}}
"""
```

### 4.4 Fallback Strategies When Extraction Fails

```python
class RobustExtractor(TwoStageExtractor):
    """
    Extractor with multiple fallback strategies
    """
    
    async def extract_with_fallbacks(
        self,
        markdown: str,
        max_attempts: int = 3
    ) -> Dict:
        """
        Try multiple extraction strategies
        """
        # Strategy 1: Two-stage extraction
        result = await self.extract(markdown)
        if self._is_valid_result(result):
            return result
        
        # Strategy 2: Regex-based extraction
        result = self._extract_with_regex(markdown)
        if self._is_valid_result(result):
            logger.info("Used regex fallback")
            return result
        
        # Strategy 3: Single-stage extraction (full document)
        result = await self._extract_single_stage(markdown)
        if self._is_valid_result(result):
            logger.info("Used single-stage fallback")
            return result
        
        # Strategy 4: Chunk-based extraction
        result = await self._extract_by_chunks(markdown)
        if self._is_valid_result(result):
            logger.info("Used chunk-based fallback")
            return result
        
        # All strategies failed
        logger.error("All extraction strategies failed")
        return self._empty_result()
    
    def _extract_with_regex(self, markdown: str) -> Dict:
        """
        Fallback: Use regex patterns for common formats
        """
        import re
        
        result = {
            "corresponding_author": {},
            "confidence": 0.5
        }
        
        # Email patterns
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, markdown)
        if emails:
            # Prefer emails near "correspondence" keyword
            result["corresponding_author"]["email"] = emails[0]
        
        # Phone patterns
        phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}',
            r'Tel[:\s]+([+\d\s\-()]+)',
            r'Phone[:\s]+([+\d\s\-()]+)',
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, markdown)
            if phones:
                result["corresponding_author"]["phone"] = phones[0]
                break
        
        return result
    
    async def _extract_single_stage(
        self,
        markdown: str,
        max_tokens: int = 50000
    ) -> Dict:
        """
        Fallback: Single-stage extraction (simpler but may fail on long docs)
        """
        truncated = truncate_to_token_limit(markdown, max_tokens, is_chinese=True)
        
        prompt = f"""
Extract corresponding author contact information from this paper:

{truncated}

Return JSON:
{{
  "name": "author name",
  "email": "email",
  "phone": "phone",
  "institution": "institution",
  "address": "address"
}}
"""
        
        response = await self.llm.call(
            prompt,
            response_format={"type": "json_object"}
        )
        
        try:
            data = json.loads(response)
            return {
                "corresponding_author": data,
                "confidence": 0.6
            }
        except:
            return self._empty_result()
    
    async def _extract_by_chunks(
        self,
        markdown: str,
        chunk_size: int = 10000
    ) -> Dict:
        """
        Fallback: Extract by processing document in chunks
        """
        chunks = [
            markdown[i:i+chunk_size]
            for i in range(0, len(markdown), chunk_size)
        ]
        
        results = []
        for i, chunk in enumerate(chunks[:5]):  # Limit to first 5 chunks
            result = await self._extract_single_stage(chunk, max_tokens=5000)
            if self._is_valid_result(result):
                results.append(result)
        
        if not results:
            return self._empty_result()
        
        # Merge results (prefer first valid extraction)
        merged = results[0]
        for result in results[1:]:
            for key, value in result["corresponding_author"].items():
                if not merged["corresponding_author"].get(key) and value:
                    merged["corresponding_author"][key] = value
        
        merged["confidence"] = 0.5
        return merged
    
    def _is_valid_result(self, result: Dict) -> bool:
        """Check if extraction result is valid"""
        author = result.get("corresponding_author", {})
        
        # At minimum, need name or email
        return bool(author.get("name") or author.get("email"))
```

### 4.5 Common Gotchas & Pitfalls

#### 1. Not Validating JSON Response

```python
# ❌ WRONG: Direct JSON parsing without validation
data = json.loads(response)
email = data["email"]  # May raise KeyError

# ✅ CORRECT: Validate response structure
try:
    data = json.loads(response)
    email = data.get("email")  # Safe access
    if not email:
        logger.warning("Email not found in extraction")
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON response: {e}")
    data = {}
```

#### 2. Not Handling Token Overflow

```python
# ❌ WRONG: Send full document without checking size
response = await llm.call(f"Extract from: {full_document}")

# ✅ CORRECT: Check and truncate
if estimate_tokens(full_document) > 100000:
    truncated = truncate_to_token_limit(full_document, 90000)
    response = await llm.call(f"Extract from: {truncated}")
```

#### 3. Not Handling Multilingual Content

```python
# ❌ WRONG: Assume English-only
email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'

# ✅ CORRECT: Handle multilingual
email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# Also handle Chinese phone numbers
phone_pattern = r'(?:\+86[-\s]?)?(?:\d{3,4}[-\s]?)?\d{7,8}'
```

### 4.6 Performance Optimization Tips

#### 1. Cache LLM Responses

```python
import hashlib

class CachedExtractor(TwoStageExtractor):
    def __init__(self, llm_client, cache_dir: str = "data/extraction_cache"):
        super().__init__(llm_client)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, markdown: str, stage: str) -> str:
        """Generate cache key for markdown"""
        content_hash = hashlib.md5(markdown.encode()).hexdigest()
        return self.cache_dir / f"{content_hash}_{stage}.json"
    
    async def _locate_keywords(self, markdown: str) -> Optional[LocationInfo]:
        # Check cache
        cache_file = self._get_cache_key(markdown, "stage1")
        
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
                return LocationInfo(**data)
        
        # Call LLM
        result = await super()._locate_keywords(markdown)
        
        # Save to cache
        if result:
            with open(cache_file, 'w') as f:
                json.dump(result.__dict__, f)
        
        return result
```

#### 2. Parallel Extraction for Multiple Papers

```python
import asyncio

async def extract_batch(
    markdowns: List[str],
    max_concurrent: int = 5
) -> List[Dict]:
    """
    Extract from multiple papers in parallel
    """
    extractor = TwoStageExtractor(llm_client)
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def extract_with_limit(markdown: str) -> Dict:
        async with semaphore:
            return await extractor.extract(markdown)
    
    tasks = [extract_with_limit(md) for md in markdowns]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Extraction failed for paper {i}: {result}")
            processed.append(extractor._empty_result())
        else:
            processed.append(result)
    
    return processed
```

---

## Section 5: Incremental Crawling

### 5.1 Field Completeness Validation Patterns

```python
# src/pipeline/validators.py
"""
Field Completeness Validation

Purpose: Determine if a paper lead has all required fields
Strategy: Define required fields and validation rules
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class FieldStatus(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"

@dataclass
class FieldValidationResult:
    status: FieldStatus
    missing_fields: List[str]
    empty_fields: List[str]
    completeness_score: float  # 0.0 - 1.0

class FieldCompletenessValidator:
    """
    Validates if a paper lead has all required fields
    """
    
    # Required fields for a complete lead
    REQUIRED_FIELDS = [
        "title",
        "published_at",
        "article_url",
        "source",
        "name",          # Corresponding author name
        "address",
        "phone",
        "email"
    ]
    
    # Optional fields (nice to have)
    OPTIONAL_FIELDS = [
        "institution",
        "all_authors",
        "doi",
        "pmid"
    ]
    
    def validate(self, lead: Dict) -> FieldValidationResult:
        """
        Validate lead completeness
        """
        missing = []
        empty = []
        
        for field in self.REQUIRED_FIELDS:
            value = lead.get(field)
            
            if value is None:
                missing.append(field)
            elif isinstance(value, str) and value.strip() == "":
                empty.append(field)
        
        # Calculate completeness score
        total_required = len(self.REQUIRED_FIELDS)
        complete_fields = total_required - len(missing) - len(empty)
        score = complete_fields / total_required
        
        # Determine status
        if len(missing) == 0 and len(empty) == 0:
            status = FieldStatus.COMPLETE
        elif complete_fields > 0:
            status = FieldStatus.PARTIAL
        else:
            status = FieldStatus.EMPTY
        
        return FieldValidationResult(
            status=status,
            missing_fields=missing,
            empty_fields=empty,
            completeness_score=score
        )
    
    def needs_reextraction(self, lead: Dict) -> bool:
        """
        Determine if lead needs re-extraction
        """
        result = self.validate(lead)
        
        # Re-extract if:
        # 1. Not complete
        # 2. Has at least some data (don't retry complete failures)
        return (
            result.status != FieldStatus.COMPLETE and
            result.completeness_score > 0.3  # At least 30% complete
        )
    
    def get_fields_to_extract(self, lead: Dict) -> List[str]:
        """
        Get list of fields that need extraction
        """
        result = self.validate(lead)
        return result.missing_fields + result.empty_fields

# Usage in pipeline
validator = FieldCompletenessValidator()

async def process_lead(self, doi: str):
    """
    Process lead with completeness check
    """
    # Check if lead exists
    lead = await self.db.get_lead_by_doi(doi)
    
    if lead:
        # Validate completeness
        validation = validator.validate(lead)
        
        if validation.status == FieldStatus.COMPLETE:
            logger.info(f"Lead {doi} is complete, skipping")
            return None
        
        logger.info(
            f"Lead {doi} is {validation.status.value} "
            f"(score: {validation.completeness_score:.2f}), "
            f"missing: {validation.missing_fields}"
        )
        
        # Determine if we should re-extract
        if validator.needs_reextraction(lead):
            # Get fields to extract
            fields_needed = validator.get_fields_to_extract(lead)
            
            # Re-extract from cached markdown
            markdown = await self.get_raw_markdown(doi)
            if markdown:
                extracted = await self.extractor.extract(markdown)
                
                # Update only missing fields
                updates = {
                    k: v for k, v in extracted.items()
                    if k in fields_needed
                }
                
                await self.db.update_lead(doi, updates)
                
                # Notify about updates
                await self.notify_field_updates(doi, updates)
```

### 5.2 Efficient Diff Detection for Database Updates

```python
# src/pipeline/diff_detector.py
"""
Diff Detection for Incremental Updates

Purpose: Detect what changed between old and new data
Strategy: Compare fields and generate human-readable diff
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime
import json

@dataclass
class FieldDiff:
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str  # "added", "removed", "modified"

@dataclass
class LeadDiff:
    doi: str
    diffs: List[FieldDiff]
    timestamp: datetime
    summary: str

class DiffDetector:
    """
    Detects changes between old and new lead data
    """
    
    # Fields to ignore in diff (metadata)
    IGNORED_FIELDS = {
        "id",
        "created_at",
        "updated_at",
        "score"  # Recalculated, not extracted
    }
    
    def detect_changes(
        self,
        old_lead: Dict,
        new_lead: Dict
    ) -> LeadDiff:
        """
        Detect what changed between old and new data
        """
        diffs = []
        
        # Get all field names
        all_fields = set(old_lead.keys()) | set(new_lead.keys())
        relevant_fields = all_fields - self.IGNORED_FIELDS
        
        for field in relevant_fields:
            old_value = old_lead.get(field)
            new_value = new_lead.get(field)
            
            # Normalize values for comparison
            old_normalized = self._normalize_value(old_value)
            new_normalized = self._normalize_value(new_value)
            
            if old_normalized != new_normalized:
                change_type = self._determine_change_type(
                    old_normalized,
                    new_normalized
                )
                
                diffs.append(FieldDiff(
                    field_name=field,
                    old_value=old_value,
                    new_value=new_value,
                    change_type=change_type
                ))
        
        # Generate summary
        summary = self._generate_summary(diffs)
        
        return LeadDiff(
            doi=old_lead.get("doi") or new_lead.get("doi"),
            diffs=diffs,
            timestamp=datetime.now(),
            summary=summary
        )
    
    def _normalize_value(self, value: Any) -> Any:
        """
        Normalize value for comparison
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            # Trim whitespace, normalize case for emails
            normalized = value.strip()
            if "@" in normalized:
                normalized = normalized.lower()
            return normalized
        
        if isinstance(value, (list, dict)):
            # Sort lists, sort dict keys for comparison
            return json.dumps(value, sort_keys=True)
        
        return value
    
    def _determine_change_type(
        self,
        old_value: Any,
        new_value: Any
    ) -> str:
        """
        Determine the type of change
        """
        if old_value is None and new_value is not None:
            return "added"
        
        if old_value is not None and new_value is None:
            return "removed"
        
        return "modified"
    
    def _generate_summary(self, diffs: List[FieldDiff]) -> str:
        """
        Generate human-readable summary
        """
        if not diffs:
            return "No changes detected"
        
        added = [d for d in diffs if d.change_type == "added"]
        removed = [d for d in diffs if d.change_type == "removed"]
        modified = [d for d in diffs if d.change_type == "modified"]
        
        parts = []
        
        if added:
            parts.append(f"Added: {', '.join(d.field_name for d in added)}")
        
        if removed:
            parts.append(f"Removed: {', '.join(d.field_name for d in removed)}")
        
        if modified:
            parts.append(f"Updated: {', '.join(d.field_name for d in modified)}")
        
        return "; ".join(parts)

# Usage
detector = DiffDetector()

async def update_lead_with_diff(self, doi: str, new_data: Dict):
    """
    Update lead and track changes
    """
    # Get old data
    old_lead = await self.db.get_lead_by_doi(doi)
    
    # Detect changes
    diff = detector.detect_changes(old_lead, new_data)
    
    if diff.diffs:
        # Update database
        await self.db.update_lead(doi, new_data)
        
        # Log changes
        logger.info(f"Updated {doi}: {diff.summary}")
        
        # Send notification
        await self.send_update_notification(diff)
        
        # Store diff history
        await self.db.save_diff_history(diff)
    else:
        logger.info(f"No changes for {doi}, skipping update")
```

### 5.3 Notification Strategies for Field Updates

```python
# src/notifications/update_notifier.py
"""
Notification System for Field Updates

Purpose: Notify users when leads are updated
Strategy: Generate informative notifications with context
"""

from typing import List, Dict
from dataclasses import dataclass
from enum import Enum
import asyncio

class NotificationChannel(Enum):
    FEISHU = "feishu"
    EMAIL = "email"
    WEBHOOK = "webhook"

@dataclass
class Notification:
    channel: NotificationChannel
    title: str
    message: str
    metadata: Dict

class UpdateNotifier:
    """
    Sends notifications when leads are updated
    """
    
    def __init__(self, config: Dict):
        self.feishu_webhook = config.get("feishu_webhook")
        self.email_recipients = config.get("email_recipients", [])
        self.webhook_url = config.get("webhook_url")
        
        # Rate limiting
        self.notification_queue = []
        self.batch_interval = 300  # 5 minutes
    
    async def notify_field_updates(
        self,
        diff: LeadDiff,
        channels: List[NotificationChannel] = None
    ):
        """
        Send notifications about field updates
        """
        if not channels:
            channels = [NotificationChannel.FEISHU]
        
        # Generate notification content
        notification = self._create_notification(diff)
        
        # Send to each channel
        tasks = []
        
        if NotificationChannel.FEISHU in channels:
            tasks.append(self._send_feishu(notification))
        
        if NotificationChannel.EMAIL in channels:
            tasks.append(self._send_email(notification))
        
        if NotificationChannel.WEBHOOK in channels:
            tasks.append(self._send_webhook(notification))
        
        # Send in parallel
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _create_notification(self, diff: LeadDiff) -> Notification:
        """
        Create notification from diff
        """
        # Format title
        title = f"📝 线索更新: {diff.doi}"
        
        # Format message
        message_lines = [
            f"**更新时间**: {diff.timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"**变更摘要**: {diff.summary}",
            "",
            "**详细变更**:"
        ]
        
        for field_diff in diff.diffs:
            emoji = self._get_change_emoji(field_diff.change_type)
            message_lines.append(
                f"{emoji} **{field_diff.field_name}**"
            )
            
            if field_diff.change_type == "added":
                message_lines.append(
                    f"  → 新增: `{field_diff.new_value}`"
                )
            elif field_diff.change_type == "removed":
                message_lines.append(
                    f"  → 移除: `{field_diff.old_value}`"
                )
            else:
                message_lines.extend([
                    f"  旧值: `{field_diff.old_value}`",
                    f"  新值: `{field_diff.new_value}`"
                ])
        
        message = "\n".join(message_lines)
        
        return Notification(
            channel=NotificationChannel.FEISHU,
            title=title,
            message=message,
            metadata={
                "doi": diff.doi,
                "change_count": len(diff.diffs),
                "timestamp": diff.timestamp.isoformat()
            }
        )
    
    def _get_change_emoji(self, change_type: str) -> str:
        """Get emoji for change type"""
        return {
            "added": "✅",
            "removed": "❌",
            "modified": "📝"
        }.get(change_type, "•")
    
    async def _send_feishu(self, notification: Notification):
        """
        Send notification to Feishu
        """
        import httpx
        
        if not self.feishu_webhook:
            return
        
        # Feishu card format
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": notification.title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": notification.message
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "查看详情"
                                },
                                "url": f"https://doi.org/{notification.metadata['doi']}",
                                "type": "primary"
                            }
                        ]
                    }
                ]
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.feishu_webhook,
                json=card
            )
            
            if response.status_code != 200:
                logger.error(f"Feishu notification failed: {response.text}")
    
    async def _send_email(self, notification: Notification):
        """
        Send notification via email
        """
        # Implement email sending
        pass
    
    async def _send_webhook(self, notification: Notification):
        """
        Send notification to webhook
        """
        import httpx
        
        if not self.webhook_url:
            return
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json={
                    "title": notification.title,
                    "message": notification.message,
                    "metadata": notification.metadata
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Webhook notification failed: {response.text}")

# Batch notification for multiple updates
class BatchNotifier(UpdateNotifier):
    """
    Batch multiple notifications together
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_notifications = []
        self.batch_size = 10
        self.last_sent = datetime.now()
    
    async def queue_notification(self, diff: LeadDiff):
        """
        Queue notification for batch sending
        """
        notification = self._create_notification(diff)
        self.pending_notifications.append(notification)
        
        # Send batch if size reached or time elapsed
        should_send = (
            len(self.pending_notifications) >= self.batch_size or
            (datetime.now() - self.last_sent).seconds > self.batch_interval
        )
        
        if should_send:
            await self.send_batch()
    
    async def send_batch(self):
        """
        Send batched notifications
        """
        if not self.pending_notifications:
            return
        
        # Combine notifications
        combined = self._combine_notifications(self.pending_notifications)
        
        # Send combined notification
        await self._send_feishu(combined)
        
        # Clear queue
        self.pending_notifications = []
        self.last_sent = datetime.now()
    
    def _combine_notifications(
        self,
        notifications: List[Notification]
    ) -> Notification:
        """
        Combine multiple notifications into one
        """
        count = len(notifications)
        title = f"📝 {count} 个线索已更新"
        
        message_lines = [
            f"**更新数量**: {count}",
            "",
            "**更新列表**:"
        ]
        
        for i, notif in enumerate(notifications[:10], 1):  # Limit to 10
            doi = notif.metadata["doi"]
            change_count = notif.metadata["change_count"]
            message_lines.append(
                f"{i}. `{doi}` - {change_count} 个字段更新"
            )
        
        if count > 10:
            message_lines.append(f"... 还有 {count - 10} 个线索")
        
        return Notification(
            channel=NotificationChannel.FEISHU,
            title=title,
            message="\n".join(message_lines),
            metadata={"count": count}
        )
```

### 5.4 Common Gotchas & Pitfalls

#### 1. Not Handling NULL Values in Completeness Check

```python
# ❌ WRONG: Only checks for None
if lead["email"]:
    # This will fail if email is empty string ""

# ✅ CORRECT: Check both None and empty
if lead.get("email") and lead["email"].strip():
    # This handles both None and empty strings
```

#### 2. Over-Notification

```python
# ❌ WRONG: Send notification for every tiny update
await notify(diff)  # Called for every field change

# ✅ CORRECT: Batch notifications
await notifier.queue_notification(diff)

# Or only notify for important fields
IMPORTANT_FIELDS = {"email", "phone", "name"}
if any(d.field_name in IMPORTANT_FIELDS for d in diff.diffs):
    await notify(diff)
```

#### 3. Infinite Re-extraction Loop

```python
# ❌ WRONG: Keep retrying even if extraction always fails
while not is_complete(lead):
    lead = await reextract(lead)

# ✅ CORRECT: Limit retry attempts
max_attempts = 3
attempts = lead.get("extraction_attempts", 0)

if attempts < max_attempts:
    lead = await reextract(lead)
    lead["extraction_attempts"] = attempts + 1
else:
    logger.warning(f"Giving up on {lead['doi']} after {attempts} attempts")
```

### 5.5 Performance Optimization Tips

#### 1. Use Database Indexes for Quick Checks

```sql
-- Create index for quick completeness checks
CREATE INDEX idx_paper_leads_complete 
ON paper_leads(doi) 
WHERE 
    title IS NOT NULL AND
    published_at IS NOT NULL AND
    email IS NOT NULL AND
    phone IS NOT NULL;

-- Query for incomplete leads quickly
SELECT * FROM paper_leads
WHERE NOT (
    title IS NOT NULL AND
    published_at IS NOT NULL AND
    email IS NOT NULL AND
    phone IS NOT NULL
);
```

#### 2. Batch Completeness Checks

```python
async def batch_check_completeness(
    self,
    dois: List[str]
) -> Dict[str, FieldStatus]:
    """
    Check completeness for multiple leads in one query
    """
    query = """
    SELECT 
        doi,
        (title IS NOT NULL AND published_at IS NOT NULL AND 
         email IS NOT NULL AND phone IS NOT NULL) as is_complete
    FROM paper_leads
    WHERE doi = ANY($1)
    """
    
    results = await self.db.fetch(query, dois)
    
    return {
        row["doi"]: (
            FieldStatus.COMPLETE if row["is_complete"] 
            else FieldStatus.PARTIAL
        )
        for row in results
    }
```

#### 3. Cache Completeness Status

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_completeness(self, doi: str) -> FieldStatus:
    """
    Cache completeness status to avoid repeated checks
    """
    lead = self.db.get_lead_by_doi(doi)
    result = self.validator.validate(lead)
    return result.status

# Invalidate cache on update
def update_lead(self, doi: str, updates: Dict):
    self.db.update_lead(doi, updates)
    self.get_cached_completeness.cache_clear()
```

---

## Summary & Key Takeaways

### Critical Implementation Points

1. **Database Migration**
   - Always backup before migration
   - Use transactions and test rollback
   - Create indexes AFTER data operations
   - Use UNIQUE constraints with NULL handling

2. **PubMed Entrez API**
   - Implement rate limiting (3 req/s without key, 10 req/s with key)
   - Use exponential backoff for retries
   - Batch requests (max 200 PMIDs per efetch)
   - Cache common queries

3. **NCBI ID Converter**
   - Batch size: 100-200 PMIDs
   - Handle missing DOIs gracefully
   - Check status field in responses
   - Cache conversion results

4. **Two-Stage Extraction**
   - Stage 1: Locate (max 50K tokens)
   - Stage 2: Extract (max 10K tokens)
   - Implement fallback strategies (regex, chunks)
   - Validate JSON responses

5. **Incremental Crawling**
   - Define required fields explicitly
   - Track extraction attempts to avoid loops
   - Batch notifications
   - Use database indexes for quick checks

### Performance Optimization Checklist

- [ ] Implement connection pooling
- [ ] Use batch inserts/updates
- [ ] Add appropriate indexes
- [ ] Cache LLM responses
- [ ] Implement rate limiting
- [ ] Use async/await throughout
- [ ] Batch API requests
- [ ] Cache completeness status
- [ ] Batch notifications

### Monitoring & Alerting

- [ ] Track extraction success rate
- [ ] Monitor API rate limit hits
- [ ] Alert on extraction failures
- [ ] Track database migration status
- [ ] Monitor notification delivery

---

**Document Version**: 1.0
**Last Updated**: 2026-03-12
**Author**: Research Subagent
**Status**: Complete
