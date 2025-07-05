# Deployment Guide: Railway + GitHub Actions

This guide will help you deploy your Stanford Research Opportunities app to Railway with daily scraping via GitHub Actions.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Account**: For GitHub Actions
3. **Google Gemini API Key**: For LLM parsing (optional but recommended)

## Step 1: Prepare Your Repository

### 1.1 Environment Variables

Create a `.env` file in your root directory with the following variables:

```bash
# Database
POSTGRES_DB=stanford_opportunities
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secret_key_here

# App Configuration
ENABLE_LLM_PARSING=true
DEBUG=false

# Frontend
REACT_APP_API_URL=https://your-app-name.railway.app
```

### 1.2 Update Frontend API URL

Update your frontend to use the production API URL. In `frontend/src/config/api.ts` (create if it doesn't exist):

```typescript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  opportunities: `${API_BASE_URL}/api/opportunities`,
  scraping: `${API_BASE_URL}/api/opportunities/scrape`,
  // Add other endpoints as needed
};
```

## Step 2: Deploy to Railway

### 2.1 Connect Your Repository

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect your `docker-compose.prod.yml`

### 2.2 Configure Environment Variables

In your Railway project dashboard:

1. Go to the "Variables" tab
2. Add all the environment variables from your `.env` file
3. Make sure to set `POSTGRES_PASSWORD` to a secure password

### 2.3 Deploy

1. Railway will automatically build and deploy your app
2. Monitor the deployment logs for any issues
3. Once deployed, note your app's URL (e.g., `https://your-app-name.railway.app`)

## Step 3: Set Up GitHub Actions

### 3.1 Add Repository Secrets

In your GitHub repository:

1. Go to Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `RAILWAY_URL`: Your Railway app URL (e.g., `https://your-app-name.railway.app`)
   - `SCRAPING_API_KEY`: A secure API key for triggering scraping

### 3.2 Create API Key for Scraping

Add an API key endpoint to your backend. In `backend/app/api/opportunities.py`, add:

```python
from fastapi import HTTPException, Header

@router.post("/scrape/trigger")
async def trigger_scraping_via_github_actions(
    authorization: str = Header(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Trigger scraping via GitHub Actions with API key authentication."""
    
    # Verify API key
    expected_key = os.getenv("SCRAPING_API_KEY")
    if not expected_key or authorization != f"Bearer {expected_key}":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Start scraping
    return await start_scraping(background_tasks=background_tasks, db=db)
```

### 3.3 Test GitHub Actions

1. Go to your GitHub repository
2. Navigate to Actions tab
3. Find the "Daily Scraping" workflow
4. Click "Run workflow" to test it manually

## Step 4: Monitor and Maintain

### 4.1 Health Checks

Your app includes health check endpoints:
- Backend: `https://your-app-name.railway.app/health`
- Frontend: `https://your-app-name.railway.app`

### 4.2 Logs and Monitoring

- **Railway Logs**: View in Railway dashboard
- **GitHub Actions Logs**: View in GitHub Actions tab
- **Database**: Access via Railway's PostgreSQL service

### 4.3 Scaling

Railway automatically scales based on traffic. You can also:
- Upgrade your plan for more resources
- Add custom domains
- Set up monitoring and alerts

## Step 5: Optional Enhancements

### 5.1 Custom Domain

1. In Railway dashboard, go to your project
2. Click on your service
3. Go to "Settings" → "Domains"
4. Add your custom domain

### 5.2 Email Notifications

Add email notifications for scraping results:

```python
# In your scraping tasks
from ..services.email_service import send_scraping_report

@celery_app.task(bind=True)
def run_daily_scraping(self):
    # ... existing code ...
    
    # Send email report
    if total_opportunities > 0:
        send_scraping_report({
            "total_opportunities": total_opportunities,
            "successful_scrapes": successful_scrapes,
            "failed_scrapes": failed_scrapes
        })
```

### 5.3 Slack/Discord Notifications

Add notifications to your GitHub Actions workflow:

```yaml
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Troubleshooting

### Common Issues

1. **Build Failures**: Check Railway build logs for missing dependencies
2. **Database Connection**: Ensure PostgreSQL service is running and credentials are correct
3. **Scraping Failures**: Check if target websites are accessible and not blocking requests
4. **Memory Issues**: Upgrade Railway plan if you encounter memory limits

### Debug Commands

```bash
# Check Railway logs
railway logs

# Access database
railway connect

# Restart services
railway service restart
```

## Cost Optimization

### Railway Pricing
- **Free Tier**: $5 credit/month
- **Pro Plan**: $20/month for more resources
- **Team Plan**: $20/user/month

### Cost-Saving Tips
1. Use Railway's free tier for development
2. Optimize Docker images to reduce build time
3. Use efficient database queries
4. Implement caching to reduce API calls

## Security Considerations

1. **Environment Variables**: Never commit sensitive data to Git
2. **API Keys**: Rotate keys regularly
3. **Database**: Use strong passwords and limit access
4. **CORS**: Configure properly for production
5. **Rate Limiting**: Implement to prevent abuse

## Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **GitHub Actions Docs**: [docs.github.com/en/actions](https://docs.github.com/en/actions)
- **FastAPI Docs**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)

---

Your app should now be deployed and running with daily scraping! 🚀 