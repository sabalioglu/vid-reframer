# Video CV Pipeline - Frontend

Modern web interface for AI-powered video scene detection and frame extraction.

## Features

- 🎨 Beautiful Tailwind CSS UI
- 🔐 API key authentication
- 📹 Drag & drop video upload
- 🤖 Real-time processing status
- 🖼️ Frame gallery viewer
- 📊 Video metadata display

## Tech Stack

- HTML5 + Vanilla JavaScript
- Tailwind CSS (CDN)
- Modal API backend
- Netlify hosting

## Local Development

Simply open `app.html` in your browser. No build step required!

```bash
# Serve locally with Python
python3 -m http.server 8000

# Or with Node.js
npx http-server -p 8000
```

Visit: http://localhost:8000/app.html

## Deploy to Netlify

### Option 1: Netlify CLI

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --prod
```

### Option 2: Netlify Dashboard

1. Go to https://app.netlify.com
2. Click "Add new site" → "Import an existing project"
3. Connect your Git repository
4. Build settings:
   - Build command: (leave empty)
   - Publish directory: `frontend`
5. Deploy!

### Option 3: Drag & Drop

1. Go to https://app.netlify.com/drop
2. Drag the `frontend` folder
3. Done!

## Environment Variables

No environment variables needed! The Modal API URL is hardcoded in `app.html`:

```javascript
const API_URL = 'https://sabalioglu--video-cv-pipeline-fastapi-app.modal.run';
```

Update this URL if you redeploy Modal to a different endpoint.

## API Endpoints Used

- `POST /register` - Create user & get API key
- `POST /upload` - Upload & process video
- `GET /videos` - List user's videos
- `GET /video/{id}` - Get specific video

## Browser Support

- Chrome/Edge: ✅
- Firefox: ✅
- Safari: ✅
- Mobile: ✅

## File Structure

```
frontend/
├── app.html           # Main application
├── netlify.toml       # Netlify configuration
└── README.md          # This file
```

## Customization

### Change Colors

Edit Tailwind classes in `app.html`:
- Primary: `blue-600` → `purple-600`
- Background: `from-slate-900 via-purple-900`

### Update Modal URL

```javascript
// In app.html
const API_URL = 'YOUR-NEW-MODAL-URL';
```

### Add Analytics

Add to `<head>` in `app.html`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

## Troubleshooting

### CORS Errors

Modal API has CORS enabled for all origins. If you see CORS errors:
1. Check Modal deployment logs
2. Verify API URL is correct
3. Check browser console for details

### API Key Not Working

1. Check localStorage: `localStorage.getItem('api_key')`
2. Re-register if needed
3. Check Network tab for 401 errors

### Video Upload Fails

1. Check file size (max 100MB)
2. Check file type (must be video/*)
3. Check Modal logs: `modal app logs video-cv-pipeline`

## License

MIT
