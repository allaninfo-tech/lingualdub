# LingualDub Website

A modern React + Tailwind CSS web application and documentation portal for the LingualDub speech-AI framework.

## Project Structure

- `public/logo.png`: Official LingualDub logo.
- `src/App.tsx`: Landing page with overview, core abstractions, and research modules.
- `wrangler.toml`: Cloudflare Pages configuration.

## Development

```bash
cd website
npm install
npm run dev
```

## Deploying to Cloudflare Pages with Wrangler

You can deploy directly to Cloudflare Pages (`lingualdub.pages.dev`) from your local terminal using **Wrangler**:

### 1. Build the static distribution:
```bash
npm run build
```

### 2. Deploy with Wrangler:
```bash
npx wrangler pages deploy dist --project-name=lingualdub
```
