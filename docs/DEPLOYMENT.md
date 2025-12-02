# Production Deployment Guide

Complete guide to deploy the Pair Programming App to production with Railway, Supabase, and custom domain.

## Architecture Overview

```
Production Stack:
├── Backend API: Railway (api.riddhigangbhoj.com)
├── Database: Supabase PostgreSQL
├── Frontend: Vercel/Netlify (app.riddhigangbhoj.com)
└── Domain: riddhigangbhoj.com
```

---

## Prerequisites

- [ ] Railway account (https://railway.app)
- [ ] Supabase account with project created
- [ ] Domain registrar access for riddhigangbhoj.com
- [ ] Git repository (push all code to GitHub)
- [ ] Vercel or Netlify account

---

## Part 1: Test Docker Build Locally

Before deploying, verify everything works locally:

```bash
# Test Docker build
cd /Users/riddhi/Documents/tredence
docker-compose up --build

# Test the API
curl http://localhost:8000/health

# Check logs
docker-compose logs -f backend

# Stop containers
docker-compose down
```

**Expected result**: Backend should start successfully and connect to PostgreSQL.

---

## Part 2: Deploy Backend to Railway

### Step 1: Create Railway Project

1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Connect your GitHub account and select your repository
4. Choose the repository: `tredence` (or your repo name)

### Step 2: Configure Environment Variables

In Railway dashboard, go to **Variables** tab and add:

```bash
# Database (from Supabase)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.lmkrhpdycpmnmwynaiox.supabase.co:5432/postgres

# CORS
ALLOWED_ORIGINS=https://app.riddhigangbhoj.com,https://riddhigangbhoj.com,https://api.riddhigangbhoj.com

# Application
DEBUG=False
SECRET_KEY=<generate-secure-random-string>

# AI (Optional)
AI_MODEL=mock
```

**Generate SECRET_KEY**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Deploy

Railway will automatically:
- Detect `nixpacks.toml` or `railway.json`
- Install dependencies
- Run database migrations (`alembic upgrade head`)
- Start the server

**Check deployment logs** to ensure:
- ✅ Database migrations ran successfully
- ✅ Server started on port $PORT
- ✅ Health check endpoint responding

---

## Part 3: Configure Custom Domain on Railway

### Step 1: Add Custom Domain in Railway

1. In Railway project, go to **Settings** > **Domains**
2. Click "Custom Domain"
3. Enter: `api.riddhigangbhoj.com`
4. Railway will show DNS records to configure

### Step 2: Configure DNS Records

Go to your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.) and add:

**For api.riddhigangbhoj.com**:
```
Type: CNAME
Name: api
Value: <railway-provided-cname> (e.g., tredence-production-xxxx.up.railway.app)
TTL: Auto or 3600
```

**DNS Propagation**: May take 5-60 minutes

**Verify DNS**:
```bash
dig api.riddhigangbhoj.com
# or
nslookup api.riddhigangbhoj.com
```

### Step 3: SSL/TLS Certificate

Railway automatically provisions SSL certificates via Let's Encrypt once DNS is configured.

**Verify HTTPS**:
```bash
curl https://api.riddhigangbhoj.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "debug": false
}
```

---

## Part 4: Run Database Migrations on Production

Migrations should run automatically on deployment (configured in `railway.json`).

**To manually run migrations**:

1. In Railway dashboard, go to project
2. Click on your service
3. Go to **Settings** > **Deploy**
4. Find the deployment logs and verify:
   ```
   INFO  [alembic.runtime.migration] Running upgrade -> 001, Initial migration
   ```

**Or use Railway CLI**:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Run migration manually
railway run alembic upgrade head
```

---

## Part 5: Deploy Frontend to Vercel

### Step 1: Prepare Frontend

Update frontend API endpoint:

```typescript
// frontend/src/config.ts or wherever API URL is defined
export const API_URL = process.env.VITE_API_URL || 'https://api.riddhigangbhoj.com';
```

Or in `.env.production`:
```
VITE_API_URL=https://api.riddhigangbhoj.com
```

### Step 2: Deploy to Vercel

1. Go to https://vercel.com/new
2. Import your Git repository
3. Configure:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

4. Add Environment Variables:
   ```
   VITE_API_URL=https://api.riddhigangbhoj.com
   ```

5. Click **Deploy**

### Step 3: Configure Custom Domain

1. In Vercel project, go to **Settings** > **Domains**
2. Add domain: `app.riddhigangbhoj.com`
3. Vercel will provide DNS records

### Step 4: Update DNS for Frontend

Add CNAME record:
```
Type: CNAME
Name: app
Value: cname.vercel-dns.com
TTL: Auto or 3600
```

**Verify**:
```bash
curl https://app.riddhigangbhoj.com
```

---

## Part 6: Update Frontend API Endpoint

Ensure frontend is calling the production API:

**In your frontend code** (`frontend/src/services/api.ts` or similar):

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.riddhigangbhoj.com';

export const createRoom = async (name: string, language: string) => {
  const response = await fetch(`${API_BASE_URL}/rooms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, language })
  });
  return response.json();
};
```

**Redeploy frontend** after updating.

---

## Part 7: Set Up Monitoring & Logging

### Option 1: Railway Logs

1. In Railway dashboard, click on your service
2. Go to **Observability** tab
3. View real-time logs

### Option 2: Sentry (Error Tracking)

1. Create account at https://sentry.io
2. Create new project (Python/FastAPI)
3. Add to `requirements.txt`:
   ```
   sentry-sdk[fastapi]==1.39.0
   ```

4. Update `main.py`:
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.fastapi import FastAPIIntegration

   if not settings.DEBUG:
       sentry_sdk.init(
           dsn=settings.SENTRY_DSN,
           integrations=[FastAPIIntegration()],
           traces_sample_rate=0.1,
       )
   ```

5. Add to Railway environment variables:
   ```
   SENTRY_DSN=https://...@sentry.io/...
   ```

### Option 3: LogTail/BetterStack

1. Sign up at https://betterstack.com/logs
2. Get source token
3. Configure Railway to forward logs

---

## Part 8: End-to-End Testing

### Test Backend API

```bash
# Health check
curl https://api.riddhigangbhoj.com/health

# Create a room
curl -X POST https://api.riddhigangbhoj.com/rooms \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Room", "language": "python"}'

# Get rooms
curl https://api.riddhigangbhoj.com/rooms

# Test WebSocket (use a WebSocket client)
wscat -c wss://api.riddhigangbhoj.com/ws/<room-id>
```

### Test Frontend

1. Open https://app.riddhigangbhoj.com
2. Create a new room
3. Test real-time collaboration
4. Open in multiple tabs/browsers
5. Verify:
   - Room creation works
   - Code synchronization works
   - WebSocket connections work
   - Autocomplete works

### Test CORS

```bash
curl -H "Origin: https://app.riddhigangbhoj.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS \
  https://api.riddhigangbhoj.com/rooms -v
```

Should see `Access-Control-Allow-Origin` header.

---

## Troubleshooting

### Issue: Railway deployment fails

**Check**:
- Review deployment logs in Railway dashboard
- Verify all environment variables are set
- Check `railway.json` and `nixpacks.toml` syntax

### Issue: Database connection errors

**Solutions**:
1. Verify `DATABASE_URL` is correct
2. Check Supabase project is running
3. Verify Supabase allows connections from Railway IPs
4. Test connection:
   ```bash
   railway run python -c "from app.database import engine; engine.connect()"
   ```

### Issue: CORS errors in browser

**Solutions**:
1. Check `ALLOWED_ORIGINS` includes your frontend URL
2. Verify HTTPS is used (not HTTP)
3. Check browser console for exact error
4. Test CORS headers with curl (see above)

### Issue: WebSocket connections fail

**Solutions**:
1. Verify Railway supports WebSockets (it does)
2. Check WSS (not WS) protocol is used
3. Review WebSocket logs in Railway
4. Test with: `wscat -c wss://api.riddhigangbhoj.com/ws/test-room`

### Issue: DNS not propagating

**Solutions**:
1. Wait 5-60 minutes for propagation
2. Clear DNS cache: `sudo dscacheutil -flushcache` (Mac)
3. Test with: `dig api.riddhigangbhoj.com`
4. Use https://dnschecker.org to check globally

### Issue: SSL certificate not working

**Solutions**:
1. Wait for Railway to provision cert (5-10 minutes after DNS)
2. Verify DNS is correctly pointing to Railway
3. Check Railway dashboard for SSL status

---

## Production Checklist

Before going live:

- [ ] All environment variables configured
- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] Database migrations applied
- [ ] Custom domains configured (api + app)
- [ ] SSL certificates active
- [ ] CORS configured correctly
- [ ] Security headers enabled
- [ ] Frontend pointing to production API
- [ ] End-to-end tests passing
- [ ] Monitoring/logging configured
- [ ] Backup strategy for database (Supabase handles this)

---

## Maintenance

### Updating the Application

1. Push changes to GitHub
2. Railway auto-deploys on push to main branch
3. Database migrations run automatically

### Manual Deployment

```bash
railway up
```

### Rolling Back

In Railway dashboard:
1. Go to **Deployments**
2. Find previous working deployment
3. Click **Redeploy**

### Database Backups

Supabase automatically backs up your database. To restore:
1. Go to Supabase Dashboard
2. Database > Backups
3. Choose backup to restore

---

## Security Best Practices

1. **Never commit secrets** - Use environment variables
2. **Keep dependencies updated** - Run `pip list --outdated`
3. **Monitor logs** - Check for suspicious activity
4. **Rate limiting** - Consider adding (e.g., slowapi)
5. **Database backups** - Verify Supabase backups are enabled
6. **Regular updates** - Keep Railway, Supabase, and dependencies updated

---

## Support & Resources

- **Railway Docs**: https://docs.railway.app
- **Supabase Docs**: https://supabase.com/docs
- **Vercel Docs**: https://vercel.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Your API Docs**: https://api.riddhigangbhoj.com/docs (if DEBUG=True)

---

## Next Steps

After deployment:
1. Set up analytics (Google Analytics, Plausible, etc.)
2. Add authentication (JWT, OAuth)
3. Implement rate limiting
4. Add caching (Redis)
5. Set up CI/CD pipelines
6. Add automated tests
7. Configure CDN for frontend assets

---

**Deployment Date**: _____________
**Deployed By**: _____________
**Production URL**: https://app.riddhigangbhoj.com
**API URL**: https://api.riddhigangbhoj.com
