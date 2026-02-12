# Frontend Integration Guide - Async Query API

## 🎯 Quick Start

Your frontend developer needs to integrate with **2 new endpoints**:

### 1. Submit Query (Instant Response)
```
POST /query/async
```

### 2. Poll for Results (Every 2 seconds)
```
GET /query/status/{task_id}
```

---

## 📋 Complete Integration Example

### React/Next.js Implementation

```javascript
import { useState, useEffect } from 'react';

function ChatInterface() {
  const [query, setQuery] = useState('');
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  // Step 1: Submit Query
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/query/async', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          top_k: 10
        })
      });
      
      const data = await response.json();
      setTaskId(data.task_id);  // Start polling
      
    } catch (error) {
      console.error('Failed to submit query:', error);
      setLoading(false);
    }
  };

  // Step 2: Poll for Status
  useEffect(() => {
    if (!taskId) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/query/status/${taskId}`
        );
        const data = await response.json();
        
        setStatus(data.status);
        setProgress(data.progress);
        
        if (data.status === 'SUCCESS') {
          setAnswer(data.answer);
          setLoading(false);
          clearInterval(pollInterval);
        } else if (data.status === 'FAILURE') {
          console.error('Query failed:', data.error);
          setLoading(false);
          clearInterval(pollInterval);
        }
        
      } catch (error) {
        console.error('Polling error:', error);
        clearInterval(pollInterval);
      }
    }, 2000);  // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [taskId]);

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question..."
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Processing...' : 'Ask'}
        </button>
      </form>

      {loading && (
        <div className="progress-bar">
          <div style={{ width: `${progress}%` }}></div>
          <p>{status} - {progress}%</p>
        </div>
      )}

      {answer && (
        <div className="answer">
          <h3>Answer:</h3>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 🔄 API Response Examples

### Submit Query Response (Instant)
```json
{
  "task_id": "abc-123-def-456",
  "status": "PENDING"
}
```

### Polling Responses

**Stage 1: Starting (0%)**
```json
{
  "task_id": "abc-123",
  "status": "PENDING",
  "progress": 0,
  "message": "Task queued, waiting to start..."
}
```

**Stage 2: Searching (30%)**
```json
{
  "task_id": "abc-123",
  "status": "PROCESSING",
  "progress": 30,
  "message": "Documents retrieved. Analyzing..."
}
```

**Stage 3: Analyzing (70%)**
```json
{
  "task_id": "abc-123",
  "status": "PROCESSING",
  "progress": 70,
  "message": "Generating answer..."
}
```

**Stage 4: Complete (100%)**
```json
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "progress": 100,
  "message": "Complete!",
  "answer": "According to SS 25268:2023, office spaces require...",
  "sources": [
    {"document": "SS_25268_2023.pdf", "page": "Table 17"}
  ],
  "metrics": {
    "retrieval_time": 3.2,
    "reranking_time": 0.8,
    "generation_time": 4.1,
    "total_time": 8.1
  }
}
```

---

## 🎨 UI/UX Recommendations

### Progress Messages
```javascript
const getProgressMessage = (progress) => {
  if (progress < 10) return "⏳ Starting...";
  if (progress < 30) return "🔍 Searching documents...";
  if (progress < 70) return "🤔 Analyzing results...";
  if (progress < 100) return "✍️ Generating answer...";
  return "✅ Complete!";
};
```

### Loading States
```css
.progress-bar {
  width: 100%;
  height: 4px;
  background: #eee;
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar > div {
  height: 100%;
  background: linear-gradient(90deg, #4285F4, #34A853);
  transition: width 0.3s ease;
}
```

---

## ⚡ Performance Tips

1. **Polling Frequency**: 2 seconds is optimal
   - Too fast (< 1s): Unnecessary server load
   - Too slow (> 3s): Poor UX

2. **Timeout**: Set max wait time
   ```javascript
   const MAX_WAIT = 60000; // 60 seconds
   const startTime = Date.now();
   
   if (Date.now() - startTime > MAX_WAIT) {
     clearInterval(pollInterval);
     showError("Request timeout");
   }
   ```

3. **Error Handling**: Always handle failures
   ```javascript
   if (data.status === 'FAILURE') {
     showError(data.error || 'Query failed');
   }
   ```

---

## 🔐 Production Checklist

- [ ] Add API authentication (X-API-Key header)
- [ ] Update CORS to allow your frontend domain
- [ ] Add rate limiting (backend)
- [ ] Implement request retry logic (frontend)
- [ ] Add analytics/tracking
- [ ] Set up error monitoring (Sentry)

---

## 📞 Backend Endpoints Reference

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|---------------|
| `/query/async` | POST | Submit query | <100ms |
| `/query/status/{task_id}` | GET | Poll status | <50ms |
| `/query` | POST | Sync query (old) | 10-15s |

**Recommendation**: Use `/query/async` for all new integrations!

---

## 🐛 Troubleshooting

### Issue: Stuck at PENDING
**Cause**: Celery worker not running
**Solution**: Start worker with `celery -A src.worker.celery_app worker --loglevel=info`

### Issue: Task ID not found
**Cause**: Redis not running or task expired
**Solution**: Ensure Redis is running on port 6379

### Issue: CORS error
**Cause**: Frontend domain not whitelisted
**Solution**: Update `allow_origins` in `api/main.py`

---

**For questions, check Swagger docs at:** `http://localhost:8000/docs`
