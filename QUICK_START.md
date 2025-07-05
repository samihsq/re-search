# Quick Start: Deploy to Railway

Get your Stanford Research Opportunities app deployed in 5 minutes!

## 🚀 Quick Deployment Steps

### 1. Prepare Environment Variables

**Option A: Automated setup (recommended)**

```bash
./setup-env.sh
```

**Option B: Manual setup**

```bash
# Copy the template
cp backend/environment.example .env

# Edit with your values
nano .env
```

**Required variables:**

- `GEMINI_API_KEY`: Your Google Gemini API key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))
- Other values are auto-generated securely

### 2. Deploy to Railway

**⚠️ Important**: Railway doesn't support Docker Compose volumes. We've created a single Dockerfile approach instead.

**Option A: Using the deployment script (recommended)**

```bash
./deploy.sh
```

**Option B: Manual deployment**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Deploy
railway up
```

### 3. Add Railway Managed Services

After your main app deploys:

1. **Add PostgreSQL**: In Railway dashboard → "New Service" → "Database" → "PostgreSQL"
2. **Add Redis**: In Railway dashboard → "New Service" → "Database" → "Redis"

Railway will automatically create `DATABASE_URL` and `REDIS_URL` environment variables.

### 4. Configure Environment Variables

In Railway dashboard → Your service → "Variables" tab, add:

- `GEMINI_API_KEY`
- `SECRET_KEY` (from your `.env` file)
- `SCRAPING_API_KEY` (from your `.env` file)
- `ENABLE_LLM_PARSING=true`
- `DEBUG=false`
- `REACT_APP_API_URL` (your Railway app URL)

### 5. Set Up GitHub Actions

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add these secrets:
   - `RAILWAY_URL`: Your Railway app URL
   - `SCRAPING_API_KEY`: The value from your Railway environment variables

### 6. Test Everything

1. Visit your Railway app URL
2. Check health: `https://your-app-name.railway.app/health`
3. Go to GitHub Actions and manually trigger the "Daily Scraping" workflow
4. Verify scraping works: `https://your-app-name.railway.app/api/opportunities/stats`

## 📋 What You Get

✅ **Full-stack app** deployed to Railway  
✅ **PostgreSQL database** with managed service  
✅ **Redis** for caching and task queue  
✅ **Daily scraping** via GitHub Actions  
✅ **LLM-enhanced parsing** (if Gemini API key provided)  
✅ **Automatic scaling** based on traffic  
✅ **Health monitoring** and error handling  
✅ **Secure API endpoints** with authentication

## 💰 Cost Breakdown

- **Railway Free Tier**: $5 credit/month
- **PostgreSQL**: ~$5/month (managed service)
- **Redis**: ~$3/month (managed service)
- **GitHub Actions**: Free for public repos
- **Google Gemini API**: Free tier available
- **Total**: ~$8-15/month depending on usage

## 🔧 Troubleshooting

**Build fails with start.sh not found error?**

- ✅ **Fixed**: The start script is now embedded directly in the Dockerfile
- No external file dependency - the script is created during build

**Build fails with VOLUME error?**

- ✅ **Fixed**: We removed Docker Compose volumes and use Railway managed services
- Use the single `Dockerfile` approach instead

**Database connection issues?**

- Ensure PostgreSQL service is added in Railway
- Check that `DATABASE_URL` is automatically set

**Redis connection fails?**

- Ensure Redis service is added in Railway
- Check that `REDIS_URL` is automatically set

**Frontend not loading?**

- Verify `REACT_APP_API_URL` points to your Railway app URL
- Check frontend build completed successfully

**GitHub Actions fails?**

- Check if RAILWAY_URL and SCRAPING_API_KEY secrets are set
- Verify the Railway app is responding to health checks

## 📚 Detailed Guides

- **Railway-Specific**: See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for detailed Railway deployment
- **Complete Guide**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for comprehensive deployment options

## 📞 Need Help?

1. Check the Railway-specific guide: [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)
2. Review Railway logs in the dashboard
3. Check GitHub Actions logs for scraping issues
4. Verify all environment variables are set correctly

---

**Your app should be live in minutes! 🎉**
