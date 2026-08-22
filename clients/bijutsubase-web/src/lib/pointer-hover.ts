const HOVER_POINTER_TYPES = new Set(['mouse', 'pen']);

let started = false;
let hoverEnabled = false;

function syncPointerHover(event: PointerEvent): void {
	const enabled = HOVER_POINTER_TYPES.has(event.pointerType);
	if (enabled === hoverEnabled) return;
	hoverEnabled = enabled;
	document.documentElement.toggleAttribute('data-pointer-hover', enabled);
}

export function initPointerHover(): void {
	if (started || typeof document === 'undefined') return;
	started = true;
	document.addEventListener('pointerover', syncPointerHover, { capture: true, passive: true });
	document.addEventListener('pointermove', syncPointerHover, { capture: true, passive: true });
	document.addEventListener('pointerdown', syncPointerHover, { capture: true, passive: true });
}
