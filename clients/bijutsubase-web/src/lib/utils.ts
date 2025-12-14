/**
 * Utility functions for BijutsuBase web client
 */

/**
 * Process tag source for display
 * @param tagSource - Raw tag source value from API
 * @returns Formatted tag source string for display
 */
export function processTagSource(tagSource: string): string {
	if (tagSource === 'onnx') {
		return 'AI Model';
	}
	return tagSource.charAt(0).toUpperCase() + tagSource.slice(1);
}

/**
 * Debounce a function call
 * @param func - The function to debounce
 * @param wait - The time to wait in milliseconds before calling the function
 * @returns A debounced version of the function
 */
export function debounce<T extends (...args: any[]) => void>(func: T, wait: number): (...args: Parameters<T>) => void {
	let timeout: ReturnType<typeof setTimeout>;
	return function(...args: Parameters<T>) {
		clearTimeout(timeout);
		timeout = setTimeout(() => func(...args), wait);
	};
}

/**
 * Convert a danbooru-style tag name to a human readable title.
 * Example: `hatsune_miku` -> `Hatsune Miku`
 */
export function humanizeTag(tag: string): string {
	return tag
		.split('_')
		.filter(Boolean)
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
}

