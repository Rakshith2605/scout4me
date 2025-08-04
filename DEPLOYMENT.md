# Vercel Deployment Guide

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **GitHub Repository**: Push your code to GitHub
3. **Firebase Setup**: Ensure your Firebase project is configured

## Environment Variables

Set these in your Vercel project settings:

```
FLASK_SECRET_KEY=your_secret_key_here
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_CLIENT_EMAIL=your_client_email
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_PRIVATE_KEY=your_private_key
```

## Deployment Steps

1. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository

2. **Configure Build Settings**:
   - Framework Preset: `Other`
   - Build Command: Leave empty (Vercel will auto-detect)
   - Output Directory: Leave empty

3. **Environment Variables**:
   - Add all the environment variables listed above
   - Make sure to include the Firebase service account details

4. **Deploy**:
   - Click "Deploy"
   - Vercel will automatically build and deploy your app

## Important Notes

- **Firebase Service Account**: You'll need to add your Firebase service account JSON as environment variables
- **Session Management**: The app uses localStorage for session management in the browser
- **Static Files**: HTML files are served as static files
- **API Routes**: All API routes are handled by the serverless function in `api/index.py`

## Troubleshooting

1. **Build Errors**: Check that all dependencies are in `requirements.txt`
2. **Firebase Errors**: Verify environment variables are set correctly
3. **CORS Issues**: The API includes CORS headers for cross-origin requests

## Local Testing

To test locally before deploying:

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy to Vercel
vercel

# Follow the prompts to configure your project
```

## Post-Deployment

1. **Test the Application**: Visit your Vercel URL
2. **Check Logs**: Monitor function logs in Vercel dashboard
3. **Update Environment Variables**: If needed, update in Vercel project settings

## Security Notes

- Keep your Firebase service account credentials secure
- Use environment variables for all sensitive data
- Consider implementing proper session management for production 