<script lang="ts">
	import type { FileResponse } from '$lib/api';
	import { updateFileRating } from '$lib/api';
	import { processTagSource } from '$lib/utils';
	import { fly } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';
	import IconEdit from '~icons/mdi/pencil';
	import TagSection from './TagSection.svelte';

	let { open = $bindable(false), file = $bindable<FileResponse>() } = $props<{ open: boolean; file: FileResponse }>();

	// Rating state management
	let isUpdatingRating = $state(false);
	let ratingError = $state<string | null>(null);
	let isEditingRating = $state(false);

	// Available rating options
	const ratingOptions = ['safe', 'sensitive', 'questionable', 'explicit'] as const;

	// Format file size
	function formatFileSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
		if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
		return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
	}

	// Format date
	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Handle rating change
	async function handleRatingChange(newRating: string) {
		// If clicking the same rating, just close edit mode
		if (newRating === file.rating) {
			isEditingRating = false;
			ratingError = null; // Clear any existing errors
			return;
		}

		if (isUpdatingRating) return;

		isUpdatingRating = true;
		ratingError = null;

		try {
			const updatedFile = await updateFileRating(file.sha256_hash, newRating);
			file = updatedFile;
			isEditingRating = false; // Close edit mode only on success
		} catch (error) {
			ratingError = error instanceof Error ? error.message : 'Failed to update rating';
			console.error('Rating update error:', error);
		} finally {
			isUpdatingRating = false;
		}
	}

	// Get rating button classes
	function getRatingButtonClasses(rating: string): string {
		const isActive = file.rating === rating;
		const baseClasses = 'px-3 py-1 text-xs font-semibold uppercase rounded-full transition-all';
		
		if (isActive) {
			switch (rating) {
				case 'safe':
					return `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200`;
				case 'sensitive':
					return `${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200`;
				case 'questionable':
					return `${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200`;
				case 'explicit':
					return `${baseClasses} bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200`;
				default:
					return `${baseClasses} bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300`;
			}
		}
		
		return `${baseClasses} bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700`;
	}
</script>

{#if open}
	<div
		class="fixed right-0 top-0 z-60 flex h-screen w-[400px] md:w-[450px] lg:w-[500px] xl:w-[550px] 2xl:w-[600px] flex-col bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-2xl"
		transition:fly={{ x: 400, duration: 200 }}
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => e.stopPropagation()}
		role="dialog"
		aria-modal="true"
		aria-label="File information panel"
		tabindex="-1"
	>
		<!-- Header -->
		<header class="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-3">
			<h3 class="text-lg font-semibold">File Info</h3>
			<button
				onclick={() => (open = false)}
				class="rounded-lg p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-white"
				aria-label="Close info panel"
			>
				<IconClose class="h-6 w-6" />
			</button>
		</header>

		<!-- Scrollable Content -->
		<div class="flex-1 overflow-y-auto px-4 py-4">
			<!-- File Information Section -->
			<section class="mb-6">
				<h4 class="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">
					File Information
				</h4>
				<div class="space-y-2 text-sm">
					<div class="flex justify-between">
						<span class="text-gray-600 dark:text-gray-400">Date Added:</span>
						<span class="text-right">{formatDate(file.date_added)}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-600 dark:text-gray-400">Size:</span>
						<span>{formatFileSize(file.file_size)}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-600 dark:text-gray-400">Dimensions:</span>
						<span>
							{#if file.width && file.height}
								{file.width} × {file.height}
							{:else}
								N/A
							{/if}
						</span>
					</div>
				<div class="flex justify-between">
					<span class="text-gray-600 dark:text-gray-400">Format:</span>
					<span class="uppercase">{file.file_ext.toLowerCase() === 'jpg' ? 'jpeg' : file.file_ext}</span>
				</div>
					<div class="flex justify-between gap-2">
						<span class="shrink-0 text-gray-600 dark:text-gray-400">Original Name:</span>
						<span class="truncate text-right" title={file.original_filename}>
							{file.original_filename}
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-600 dark:text-gray-400">Tag Source:</span>
						<span>{processTagSource(file.tag_source)}</span>
					</div>
				</div>
			</section>

		<!-- Rating Section -->
		<section class="mb-6">
			<h4 class="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">Rating</h4>
			
			{#if isEditingRating}
				<!-- Edit mode: show all rating options -->
				<div class="flex items-center gap-2">
						<div class="flex flex-wrap gap-2">
							{#each ratingOptions as rating (rating)}
								<button
									type="button"
									class={getRatingButtonClasses(rating)}
									disabled={isUpdatingRating}
									onclick={() => handleRatingChange(rating)}
									aria-label={`Set rating to ${rating}`}
									style:opacity={isUpdatingRating ? 0.6 : 1}
									style:cursor={isUpdatingRating ? 'not-allowed' : 'pointer'}
								>
									{rating}
								</button>
							{/each}
						</div>
					<button
						type="button"
						onclick={() => {
							isEditingRating = false;
							ratingError = null;
						}}
						class="rounded-lg p-1.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-white transition-colors"
						aria-label="Cancel editing rating"
						disabled={isUpdatingRating}
					>
						<IconClose class="h-4 w-4" />
					</button>
				</div>
			{:else}
				<!-- View mode: show current rating with edit button -->
				<div class="group flex items-center gap-2">
					<span class={getRatingButtonClasses(file.rating)}>
						{file.rating}
					</span>
					<button
						type="button"
						onclick={() => isEditingRating = true}
						class="rounded-lg p-1.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-white transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
						aria-label="Edit rating"
					>
						<IconEdit class="h-4 w-4" />
					</button>
				</div>
			{/if}
			
			{#if ratingError}
				<p class="mt-2 text-xs text-red-600 dark:text-red-400">
					{ratingError}
				</p>
			{/if}
		</section>

			<!-- AI Generation Section -->
			<section class="mb-6">
				<h4 class="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">
					AI Generation
				</h4>
				<div class="text-sm">
					<span
						class="inline-block rounded-full px-3 py-1 text-xs font-semibold"
						class:bg-purple-100={file.ai_generated}
						class:text-purple-800={file.ai_generated}
						class:dark:bg-purple-900={file.ai_generated}
						class:dark:text-purple-200={file.ai_generated}
						class:bg-gray-200={!file.ai_generated}
						class:text-gray-700={!file.ai_generated}
						class:dark:bg-gray-700={!file.ai_generated}
						class:dark:text-gray-300={!file.ai_generated}
					>
						{file.ai_generated ? 'Yes' : 'No'}
					</span>
				</div>
			</section>

			<!-- Tags Section -->
			<TagSection bind:file={file} />

			<!-- Hash Information Section -->
			<section class="mb-4">
				<h4 class="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">
					Hash Information
				</h4>
				<div class="space-y-3 text-sm">
					<div>
						<div class="mb-1 text-gray-600 dark:text-gray-400">MD5:</div>
						<code
							class="block break-all rounded bg-gray-200 dark:bg-gray-800 px-2 py-1 font-mono text-xs text-gray-800 dark:text-gray-300"
						>
							{file.md5_hash}
						</code>
					</div>
					<div>
						<div class="mb-1 text-gray-600 dark:text-gray-400">SHA-256:</div>
						<code
							class="block break-all rounded bg-gray-200 dark:bg-gray-800 px-2 py-1 font-mono text-xs text-gray-800 dark:text-gray-300"
						>
							{file.sha256_hash}
						</code>
					</div>
				</div>
			</section>
		</div>
	</div>
{/if}

