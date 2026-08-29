# LingualDub Website

This directory contains the source for the LingualDub project website and documentation hub. 
It is designed to be deployed to **Cloudflare Pages** (`lingualdub.pages.dev`).

## Deployment on Cloudflare Pages

When setting up your project in the Cloudflare Pages dashboard:
1. **Framework Preset:** None (or select your SSG if you upgrade this to Next.js/Docusaurus later)
2. **Build Command:** Leave blank (for static HTML) or set your build command
3. **Build output directory:** `/website` (or `/website/dist` if using a build tool)

## Current Setup
Currently, this contains a lightweight static landing page. You can later upgrade this directory to a full static site generator (like Docusaurus, Next.js, or Astro) as the framework matures.
