/**
 * Utility functions for BijutsuBase web client
 */

import { getFileStatus, type FileResponse, type ProcessingStatus } from '$lib/api';

/**
 * Result from polling - indicates what happened
 */
export type PollingResult = {
	status: ProcessingStatus;
	file: FileResponse;
	error?: string;
};

/**
 * Callback type for processing status updates
 */
export type ProcessingStatusCallback = (result: PollingResult) => void;

/**
 * Creates a polling controller for file processing status.
 * 
 * @param onUpdate - Callback called on each poll with the updated file and status
 * @param intervalMs - Polling interval in milliseconds (default: 2000)
 * @returns Object with start and stop functions
 * 
 * @example
 * ```ts
 * const poller = createProcessingPoller((result) => {
 *   file = result.file;
 *   if (result.status === 'failed') {
 *     error = result.error;
 *   }
 * });
 * 
 * // Start polling for a file
 * poller.start(file.sha256_hash);
 * 
 * // Stop polling (e.g., on component destroy)
 * poller.stop();
 * ```
 */
export function createProcessingPoller(
	onUpdate: ProcessingStatusCallback,
	intervalMs: number = 2000
): { start: (sha256: string) => void; stop: () => void; isPolling: () => boolean } {
	let interval: ReturnType<typeof setInterval> | null = null;
	let currentSha256: string | null = null;

	async function poll() {
		if (!currentSha256) return;
		
		try {
			const file = await getFileStatus(currentSha256);
			const status = file.processing_status;
			
			onUpdate({
				status,
				file,
				error: status === 'failed' ? (file.processing_error || 'Processing failed') : undefined
			});

			// Stop polling when processing is complete or failed
			if (status === 'completed' || status === 'failed') {
				stop();
			}
		} catch (err) {
			onUpdate({
				status: 'failed',
				file: { sha256_hash: currentSha256 } as FileResponse,
				error: err instanceof Error ? err.message : 'Failed to check processing status'
			});
			stop();
		}
	}

	function start(sha256: string) {
		// If already polling for the same file, don't restart
		// This prevents rapid polling loops when the $effect re-runs on file updates
		if (currentSha256 === sha256 && interval !== null) {
			return;
		}
		
		stop(); // Clear any existing interval
		currentSha256 = sha256;
		interval = setInterval(poll, intervalMs);
		// Poll immediately as well
		poll();
	}

	function stop() {
		if (interval) {
			clearInterval(interval);
			interval = null;
		}
		currentSha256 = null;
	}

	function isPolling() {
		return interval !== null;
	}

	return { start, stop, isPolling };
}

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

/**
 * Validate if a string is a valid SHA-256 hash
 * @param value - The string to validate
 * @returns true if the string is a valid 64-character hexadecimal hash
 */
export function isValidHash(value: string): boolean {
	return /^[a-f0-9]{64}$/i.test(value.trim());
}
// TODO: Use this across the project
/**
 * Format a byte count as MB (mebibytes).
 * Example: 1048576 -> "1.00 MB"
 */
export function formatBytesToMB(bytes: number, fractionDigits: number = 2): string {
	if (!Number.isFinite(bytes)) return '—';
	return `${(bytes / (1024 * 1024)).toFixed(fractionDigits)} MB`;
}
