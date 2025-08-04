# Scot4Me - Vercel Deployment

## Quick Deploy

1. **Fork/Clone this repository**
2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import this repository

3. **Add Environment Variables**:
   ```
   FLASK_SECRET_KEY=your_secret_key_here
   FIREBASE_PROJECT_ID=your_firebase_project_id
   FIREBASE_PRIVATE_KEY_ID=your_private_key_id
   FIREBASE_CLIENT_EMAIL=your_client_email
   FIREBASE_CLIENT_ID=your_client_id
   FIREBASE_PRIVATE_KEY=your_private_key
   ```

4. **Deploy** - Click "Deploy"

## Structure

- `api/index.py` - Main serverless function (handles all routes)
- `firebase_config.py` - Firebase configuration
- `index.html` - Main dashboard
- `landing.html` - Login/signup page
- `vercel.json` - Vercel configuration

## Testing

After deployment, test these endpoints:

- `/` - Main dashboard
- `/landing` - Login page
- `/api/health` - Health check
- `/api/jobs` - Get jobs

## Troubleshooting

1. **Check Vercel logs** for any errors
2. **Verify environment variables** are set correctly
3. **Test health endpoint** first: `your-domain.vercel.app/api/health`

## Features

- ✅ Job search and scraping
- ✅ Firebase database integration
- ✅ User authentication
- ✅ Professional job cards
- ✅ Mark applied/delete jobs
- ✅ Statistics tracking 