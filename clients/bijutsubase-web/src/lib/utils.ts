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

