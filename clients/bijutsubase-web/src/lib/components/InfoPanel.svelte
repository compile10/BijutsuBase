<script lang="ts">
	import type { FileResponse } from '$lib/api';
	import { updateFileRating, updateFileAiGenerated } from '$lib/api';
	import { processTagSource } from '$lib/utils';
	import { fly } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';
	import IconEdit from '~icons/mdi/pencil';
	import TagSection from './TagSection.svelte';

	// TODO: Make sure this updates the search results if there are any changes

	let { open = $bindable(false), file = $bindable<FileResponse>() } = $props<{ open: boolean; file: FileResponse }>();

	// Rating state management
	let isUpdatingRating = $state(false);
	let ratingError = $state<string | null>(null);
	let isEditingRating = $state(false);

	// AI generation state management
	let isUpdatingAi = $state(false);
	let aiError = $state<string | null>(null);
	let isEditingAi = $state(false);

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

	// Handle AI generated change
	async function handleAiGeneratedChange(newStatus: boolean) {
		// If clicking the same status, just close edit mode
		if (newStatus === file.ai_generated) {
			isEditingAi = false;
			aiError = null; // Clear any existing errors
			return;
		}

		if (isUpdatingAi) return;

		isUpdatingAi = true;
		aiError = null;

		try {
			const updatedFile = await updateFileAiGenerated(file.sha256_hash, newStatus);
			file = updatedFile;
			isEditingAi = false; // Close edit mode only on success
		} catch (error) {
			aiError = error instanceof Error ? error.message : 'Failed to update AI generated status';
			console.error('AI generated update error:', error);
		} finally {
			isUpdatingAi = false;
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
				
				{#if isEditingAi}
					<!-- Edit mode: show Yes/No options -->
					<div class="flex items-center gap-2">
						<div class="flex flex-wrap gap-2">
							<!-- Yes Button -->
							<button
								type="button"
								class="px-3 py-1 text-xs font-semibold uppercase rounded-full transition-all {file.ai_generated ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
								disabled={isUpdatingAi}
								onclick={() => handleAiGeneratedChange(true)}
								aria-label="Set AI generated to Yes"
								style:opacity={isUpdatingAi ? 0.6 : 1}
								style:cursor={isUpdatingAi ? 'not-allowed' : 'pointer'}
							>
								Yes
							</button>
							
							<!-- No Button -->
							<button
								type="button"
								class="px-3 py-1 text-xs font-semibold uppercase rounded-full transition-all {!file.ai_generated ? 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
								disabled={isUpdatingAi}
								onclick={() => handleAiGeneratedChange(false)}
								aria-label="Set AI generated to No"
								style:opacity={isUpdatingAi ? 0.6 : 1}
								style:cursor={isUpdatingAi ? 'not-allowed' : 'pointer'}
							>
								No
							</button>
						</div>
						
						<button
							type="button"
							onclick={() => {
								isEditingAi = false;
								aiError = null;
							}}
							class="rounded-lg p-1.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-white transition-colors"
							aria-label="Cancel editing AI status"
							disabled={isUpdatingAi}
						>
							<IconClose class="h-4 w-4" />
						</button>
					</div>
				{:else}
					<!-- View mode: show current status with edit button -->
					<div class="group flex items-center gap-2">
						<span
							class="inline-block rounded-full px-3 py-1 text-xs font-semibold transition-all"
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
						<button
							type="button"
							onclick={() => isEditingAi = true}
							class="rounded-lg p-1.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-white transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
							aria-label="Edit AI generated status"
						>
							<IconEdit class="h-4 w-4" />
						</button>
					</div>
				{/if}
				
				{#if aiError}
					<p class="mt-2 text-xs text-red-600 dark:text-red-400">
						{aiError}
					</p>
				{/if}
			</section>

			<!-- Pools Section -->
			{#if file.pools && file.pools.length > 0}
				<section class="mb-6">
					<h4 class="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">
						Pools
					</h4>
					<div class="flex gap-3 overflow-x-auto scrollbar-thin">
						{#each file.pools as pool (pool.id)}
							<a
								href={`/pools/${pool.id}`}
								class="group relative flex w-32 shrink-0 flex-col overflow-hidden rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 transition-all hover:shadow-md hover:border-blue-500/50 dark:hover:border-blue-400/50"
								onclick={() => (open = false)}
							>
								<div class="aspect-4/3 w-full overflow-hidden bg-gray-200 dark:bg-gray-700">
									{#if pool.thumbnail_url}
										<img
											src={pool.thumbnail_url}
											alt={pool.name}
											class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
										/>
									{:else}
										<div class="flex h-full w-full items-center justify-center text-gray-400">
											<span class="text-xs font-medium">No Cover</span>
										</div>
									{/if}
									<!-- Member count badge -->
									<div class="absolute top-2 right-2 px-1.5 py-0.5 rounded bg-black/50 text-[10px] font-medium text-white backdrop-blur-sm">
										{pool.member_count} items
									</div>
								</div>
								
								<div class="p-2.5">
									<span
										class="block truncate text-xs font-semibold text-gray-800 dark:text-gray-200 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors"
										title={pool.name}
									>
										{pool.name}
									</span>
								</div>
							</a>
						{/each}
					</div>
				</section>
			{/if}

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

