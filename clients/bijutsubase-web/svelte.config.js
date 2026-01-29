import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// adapter-node runs SvelteKit in SSR mode using Node.js
		// See https://svelte.dev/docs/kit/adapters for more information about adapters.
		adapter: adapter(),

		// Content Security Policy configuration
		// Helps protect against XSS attacks that could steal auth tokens from localStorage
		csp: {
			// Use nonces for dynamically rendered pages
			mode: 'nonce',
			directives: {
				// Default: only allow resources from the same origin
				'default-src': ['self'],
				
				// Scripts: only from same origin (SvelteKit adds nonces for inline scripts)
				'script-src': ['self'],
				
				// Styles: same origin + unsafe-inline (required for Svelte transitions)
				'style-src': ['self', 'unsafe-inline'],
				
				// Images: same origin + blob/data URLs (for canvas/image processing)
				'img-src': ['self', 'blob:', 'data:'],
				
				// Fonts: only from same origin
				'font-src': ['self'],
				
				// Fetch/XHR connections: only to same origin
				'connect-src': ['self'],
				
				// Media (video/audio): same origin + blob URLs
				'media-src': ['self', 'blob:'],
				
				// Disallow plugins (Flash, Java, etc.)
				'object-src': ['none'],
				
				// Restrict base URL to same origin
				'base-uri': ['self'],
				
				// Forms can only submit to same origin
				'form-action': ['self'],
				
				// Prevent page from being embedded in iframes (clickjacking protection)
				'frame-ancestors': ['none']
				
				// Note: 'upgrade-insecure-requests' is intentionally omitted to allow
				// HTTP access on local networks. Enable it in production with HTTPS.
			}
		}
	}
};

export default config;
