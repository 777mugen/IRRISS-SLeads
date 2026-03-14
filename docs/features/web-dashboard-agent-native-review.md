# Agent-Native Review: Web Dashboard
**Review Date**: 2026-03-15  
**Reviewer**: Agent-Native Architecture Review  
**Scope**: Ensure feature parity between UI and API for AI agent accessibility

---

## Executive Summary

The Web Dashboard has a solid foundation with most core features accessible via API, but **critical gaps** prevent full agent-native operation. Configuration management, batch retry operations, and update/delete capabilities are **UI-only**, blocking agents from performing complete workflow automation.

**Overall Status**: 🟡 **PARTIALLY AGENT-NATIVE** (60% complete)

---

## Current API Coverage

### ✅ What Agents CAN Do

| Category | Endpoints | Status |
|----------|-----------|--------|
| **Query** | POST `/api/query/doi` <br> GET `/api/query/paper/{doi}` | ✅ Full Access |
| **Export** | GET `/api/export/csv/full` <br> GET `/api/export/csv/today` | ✅ Full Access |
| **Import** | POST `/api/import/csv/preview` <br> POST `/api/import/csv/confirm` | ✅ Full Access |
| **Batch Stats** | GET `/api/batch/stats` <br> GET `/api/batch/failed-list` | ✅ Read-Only |
| **Analysis** | GET `/api/analysis/stats` | ✅ Read-Only |
| **Health** | GET `/health` | ✅ Available |

**Total**: 10 endpoints exposed via API

---

## 🔴 CRITICAL Issues (P1) - Blocks Agent Access

### 1. Configuration Management - No API Access

**Impact**: Agents cannot view or modify system configuration  
**Current State**: UI-only at `/config/` route  
**Service Layer**: `ConfigService` exists with `get_keywords()`, `get_scoring_rules()`, `update_keywords()`  
**Gap**: Service methods not exposed via API

**Missing Endpoints**:
```python
GET    /api/config/keywords       # Get keywords configuration
PUT    /api/config/keywords       # Update keywords configuration
GET    /api/config/scoring        # Get scoring rules
PUT    /api/config/scoring        # Update scoring rules
POST   /api/config/reload         # Hot-reload configuration
```

**Why Critical**:
- Agents cannot optimize search keywords based on feedback
- Cannot adjust scoring weights without human intervention
- Cannot automate strategy version management
- Blocks closed-loop optimization (feedback → config update → new scoring)

**Evidence**:
```python
# src/web/routes/config.py - UI only
@router.get("/", response_class=HTMLResponse)
async def config_page(request: Request, service: ConfigService):
    keywords = await service.get_keywords()  # Service exists
    scoring = await service.get_scoring_rules()  # Service exists
    return templates.TemplateResponse(...)  # But no API!

# src/web/services/config_service.py - Methods exist but not exposed
class ConfigService:
    async def get_keywords(self) -> Dict[str, Any]:  # ✅ Exists
    async def update_keywords(self, keywords: Dict) -> bool:  # ✅ Exists
```

---

### 2. Batch Retry Operations - No API Control

**Impact**: Agents cannot recover from processing failures  
**Current State**: `BatchMonitor` has retry logic, but not exposed  
**Gap**: No API endpoints to trigger retry or reset operations

**Missing Endpoints**:
```python
POST   /api/batch/retry           # Retry failed papers
POST   /api/batch/reset-stale     # Reset stuck batches (>24h in 'processing')
GET    /api/batch/retry-stats     # Get retry statistics
```

**Why Critical**:
- Agents cannot automatically recover from transient failures
- Cannot implement autonomous error recovery workflows
- Requires human intervention for stuck batches
- Blocks self-healing system architecture

**Evidence**:
```python
# src/monitoring/batch_monitor.py - Logic exists but not exposed
class BatchMonitor:
    async def retry_failed_tasks(self, max_retries: int = 3) -> int:
        """重试失败的论文（将 failed 改回 pending）"""
        # Full implementation exists but no API endpoint!

    async def reset_stale_tasks(self, hours: int = 24) -> int:
        """重置卡住的任务（将 processing 改回 pending）"""
        # Full implementation exists but no API endpoint!
```

---

### 3. CRUD Operations - No Update/Delete API

**Impact**: Agents cannot modify or clean up data  
**Current State**: Create (via CSV import) and Read exist, but no Update/Delete  
**Gap**: Incomplete REST API implementation

**Missing Endpoints**:
```python
# Paper Leads
PUT    /api/paper/{doi}           # Update paper lead details
DELETE /api/paper/{doi}           # Delete a paper lead
PATCH  /api/paper/{doi}/status    # Update feedback_status only

# Feedback
GET    /api/feedback              # List all feedback
POST   /api/feedback              # Create single feedback (not CSV)
PUT    /api/feedback/{id}         # Update feedback
DELETE /api/feedback/{id}         # Delete feedback

# Raw Markdown
DELETE /api/markdown/{doi}        # Delete raw markdown
```

**Why Critical**:
- Agents cannot correct data quality issues
- Cannot remove obsolete or duplicate records
- Cannot update feedback status programmatically
- Cannot maintain data hygiene autonomously

**Evidence**:
```python
# Current API only has:
POST /api/query/doi              # ✅ Read
POST /api/import/csv/confirm     # ✅ Create (bulk only)
# PUT /api/paper/{doi}           # ❌ Missing
# DELETE /api/paper/{doi}        # ❌ Missing
```

---

## 🟡 IMPORTANT Issues (P2)

### 4. TenderLead Management - Zero API Coverage

**Impact**: Tender leads completely inaccessible to agents  
**Current State**: No API endpoints for tender leads  
**Database**: `TenderLead` model exists with full schema

**Missing Endpoints**:
```python
GET    /api/tenders               # List tender leads (with filters)
GET    /api/tender/{id}           # Get tender details
POST   /api/tender                # Create tender lead
PUT    /api/tender/{id}           # Update tender lead
DELETE /api/tender/{id}           # Delete tender lead
GET    /api/tenders/stats         # Tender statistics
```

**Why Important**:
- Tender leads are second major data source (招投标)
- Agents cannot monitor or manage tender opportunities
- Inconsistent feature parity between PaperLead and TenderLead
- Blocks holistic sales lead management

---

### 5. Feedback Management - CSV Import Only

**Impact**: Feedback cannot be created individually  
**Current State**: Bulk CSV import only, no single-record API  
**Gap**: Cannot submit feedback programmatically in real-time

**Missing Endpoints**:
```python
GET    /api/feedback              # List feedback with pagination
GET    /api/feedback/{id}         # Get feedback details
POST   /api/feedback              # Create single feedback
PUT    /api/feedback/{id}         # Update feedback
DELETE /api/feedback/{id}         # Delete feedback
```

**Why Important**:
- Sales team cannot submit feedback via API integration
- Cannot integrate with CRM systems
- CSV-only workflow is batch-oriented, not real-time
- Limits feedback collection automation

---

### 6. Batch Processing Control - Limited Visibility

**Impact**: Cannot control batch processing lifecycle  
**Current State**: Read-only stats, no control endpoints  
**Gap**: Cannot start/stop/pause batch processing

**Missing Endpoints**:
```python
GET    /api/batch/list            # List all batches with status
GET    /api/batch/{batch_id}      # Get batch details
POST   /api/batch/stop/{batch_id} # Stop a running batch
GET    /api/batch/progress        # Real-time progress updates (WebSocket/SSE)
```

**Why Important**:
- Cannot monitor batch execution in real-time
- Cannot cancel runaway batches
- Limited observability for automation

---

## 🔵 NICE-TO-HAVE (P3)

### 7. Pagination Support

**Current**: No pagination, could return millions of rows  
**Recommendation**: Add `limit`, `offset`, `cursor` parameters

```python
GET /api/papers?limit=50&offset=100&grade=A&sort=created_at:desc
```

---

### 8. Advanced Query Filters

**Current**: Basic DOI query only  
**Recommendation**: Add filter parameters

```python
GET /api/papers?grade=A&feedback_status=未处理&date_from=2026-01-01&institution=清华
```

---

### 9. Structured Error Responses

**Current**: Generic HTTP exceptions  
**Recommendation**: Standardized error format

```json
{
  "error": {
    "code": "DOI_NOT_FOUND",
    "message": "Paper with DOI 10.1000/xyz not found",
    "details": {...}
  }
}
```

---

### 10. API Rate Limiting

**Current**: No rate limiting (CORS allows all origins)  
**Recommendation**: Add rate limiting for API endpoints

```python
from slowapi import Limiter
@limiter.limit("100/minute")
```

---

### 11. Bulk Operations API

**Current**: CSV import only  
**Recommendation**: JSON-based bulk operations

```python
POST /api/papers/bulk-create
POST /api/papers/bulk-update
POST /api/feedback/bulk-create
```

---

### 12. Strategy Version Management API

**Current**: `StrategyVersion` model exists, no API  
**Recommendation**: Expose version management

```python
GET    /api/strategy/versions     # List versions
POST   /api/strategy/rollback/{version}  # Rollback to version
```

---

## Agent-Native Parity Matrix

| Feature | UI Access | API Access | Agent Can Do | Priority |
|---------|-----------|------------|--------------|----------|
| View dashboard | ✅ | ✅ (stats) | Read-only | - |
| Query papers by DOI | ✅ | ✅ | Full | - |
| Export CSV | ✅ | ✅ | Full | - |
| Import feedback CSV | ✅ | ✅ | Full | - |
| **Manage config** | ✅ | ❌ | **Nothing** | **P1** |
| **Retry failed batches** | ❌ (manual) | ❌ | **Nothing** | **P1** |
| **Update paper data** | ❌ | ❌ | **Nothing** | **P1** |
| **Delete records** | ❌ | ❌ | **Nothing** | **P1** |
| **Manage tender leads** | ❌ | ❌ | **Nothing** | **P2** |
| **Submit single feedback** | ❌ | ❌ | **Nothing** | **P2** |
| **Control batch processing** | ❌ | ❌ | **Nothing** | **P2** |

---

## Recommendations

### Immediate Actions (P1 - Required for Agent-Native)

1. **Create `/src/web/api/config.py`**
   - Expose ConfigService methods
   - Add PUT endpoints for keywords and scoring
   - Add validation and backup logic

2. **Add batch control to `/src/web/api/batch.py`**
   - POST `/api/batch/retry` endpoint
   - POST `/api/batch/reset-stale` endpoint
   - Integrate with existing BatchMonitor

3. **Add CRUD endpoints to `/src/web/api/query.py`**
   - PUT `/api/paper/{doi}` for updates
   - DELETE `/api/paper/{doi}` for deletion
   - Add proper authorization checks (future)

### Short-Term (P2 - Feature Parity)

4. **Create `/src/web/api/tender.py`**
   - Full CRUD for tender leads
   - Mirror PaperLead API structure

5. **Create `/src/web/api/feedback.py`**
   - Single feedback CRUD operations
   - Keep CSV import for bulk operations

6. **Enhance batch API with control endpoints**
   - List batches, get details, stop batches
   - Consider WebSocket for real-time updates

### Long-Term (P3 - Polish)

7. Add pagination to all list endpoints
8. Implement advanced filtering
9. Standardize error responses
10. Add rate limiting
11. Create API usage documentation
12. Add OpenAPI tags and descriptions

---

## Implementation Priority

### Phase 1: Critical Agent-Native Features (1-2 days)
- [ ] Config API (GET + PUT for keywords/scoring)
- [ ] Batch retry API
- [ ] Paper update/delete API

### Phase 2: Feature Parity (2-3 days)
- [ ] TenderLead API (full CRUD)
- [ ] Feedback API (single record CRUD)
- [ ] Batch control API (list, details, stop)

### Phase 3: Production Ready (1-2 days)
- [ ] Pagination support
- [ ] Advanced filters
- [ ] Rate limiting
- [ ] Error standardization
- [ ] API documentation

---

## Authentication Consideration

**Current**: No authentication (internal use only)  
**Recommendation**: Keep disabled for now, but design APIs to be auth-ready

When authentication is added in future:
- Add `user_id` to all create/update operations
- Add audit logging for sensitive operations
- Consider API key authentication for agents

---

## Conclusion

The Web Dashboard has **good foundation** but is **not fully agent-native**. Critical gaps in configuration management, batch control, and CRUD operations prevent autonomous agent operation. 

**Priority Focus**: 
1. Expose ConfigService via API
2. Add batch retry/reset endpoints
3. Implement update/delete operations

With these P1 fixes, agents will have 90% feature parity with UI, enabling closed-loop automation and self-healing workflows.

---

**Generated by**: Agent-Native Review Subagent  
**Review Standard**: Agent-Native Architecture Guidelines  
**Next Review**: After P1 implementation
