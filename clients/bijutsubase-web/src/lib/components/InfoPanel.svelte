<script lang="ts">
	import type { FileResponse } from '$lib/api';
	import { processTagSource } from '$lib/utils';
	import { fly } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';
	import IconAccount from '~icons/mdi/account';
	import IconPalette from '~icons/mdi/palette';
	import IconCopyright from '~icons/mdi/copyright';
	import IconTag from '~icons/mdi/tag';
	import IconInformation from '~icons/mdi/information-outline';

	let { open = $bindable(false), file } = $props<{ open: boolean; file: FileResponse }>();

	// Category order for tabs
	const categoryOrder = ['character', 'artist', 'copyright', 'general', 'meta'];

	// Group tags by category
	let tagsByCategory = $derived.by(() => {
		const groups: Record<string, typeof file.tags> = {};
		for (const tag of file.tags) {
			if (!groups[tag.category]) {
				groups[tag.category] = [];
			}
			groups[tag.category].push(tag);
		}
		return groups;
	});

	// Get available categories in order
	let availableCategories = $derived(
		categoryOrder.filter((cat) => tagsByCategory[cat]?.length > 0)
	);

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

	// Capitalize first letter
	function capitalize(str: string): string {
		return str.charAt(0).toUpperCase() + str.slice(1);
	}

	// Get icon component for category
	function getCategoryIcon(category: string) {
		switch (category) {
			case 'character':
				return IconAccount;
			case 'artist':
				return IconPalette;
			case 'copyright':
				return IconCopyright;
			case 'general':
				return IconTag;
			case 'meta':
				return IconInformation;
			default:
				return IconTag;
		}
	}

	// Get color classes for category
	function getCategoryColorClasses(category: string): string {
		switch (category) {
			case 'character':
				return 'border-l-green-500';
			case 'artist':
				return 'border-l-red-500';
			case 'copyright':
				return 'border-l-violet-500';
			case 'general':
				return 'border-l-blue-500';
			case 'meta':
				return 'border-l-yellow-300';
			default:
				return 'border-l-gray-500';
		}
	}

	// Handle tag click - open search in new tab
	function handleTagClick(tagName: string) {
		const url = `/search?tags=${encodeURIComponent(tagName)}`;
		window.open(url, '_blank');
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
				<div class="text-sm">
					<span
						class="inline-block rounded-full px-3 py-1 text-xs font-semibold uppercase"
						class:bg-green-100={file.rating === 'safe'}
						class:text-green-800={file.rating === 'safe'}
						class:dark:bg-green-900={file.rating === 'safe'}
						class:dark:text-green-200={file.rating === 'safe'}
						class:bg-blue-100={file.rating === 'sensitive'}
						class:text-blue-800={file.rating === 'sensitive'}
						class:dark:bg-blue-900={file.rating === 'sensitive'}
						class:dark:text-blue-200={file.rating === 'sensitive'}
						class:bg-yellow-100={file.rating === 'questionable'}
						class:text-yellow-800={file.rating === 'questionable'}
						class:dark:bg-yellow-900={file.rating === 'questionable'}
						class:dark:text-yellow-200={file.rating === 'questionable'}
						class:bg-red-100={file.rating === 'explicit'}
						class:text-red-800={file.rating === 'explicit'}
						class:dark:bg-red-900={file.rating === 'explicit'}
						class:dark:text-red-200={file.rating === 'explicit'}
						class:bg-gray-200={file.rating === 'unknown'}
						class:text-gray-700={file.rating === 'unknown'}
						class:dark:bg-gray-700={file.rating === 'unknown'}
						class:dark:text-gray-300={file.rating === 'unknown'}
					>
						{file.rating}
					</span>
				</div>
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
			{#if file.tags.length > 0}
				<section class="mb-6">
					<h4 class="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">Tags</h4>

					<!-- All Categories Displayed -->
					<div class="space-y-3">
						{#each availableCategories as category}
							{@const Icon = getCategoryIcon(category)}
							<div class="rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-100 dark:bg-gray-800/50 p-3">
								<!-- Category Header -->
								<div class="mb-2 flex items-center gap-2">
									<Icon class="h-4 w-4 text-gray-600 dark:text-gray-400" />
									<span class="text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-300">
										{capitalize(category)}
									</span>
									<span class="text-xs text-gray-500 dark:text-gray-500">
										({tagsByCategory[category].length})
									</span>
								</div>
								
								<!-- Tags for this Category -->
								<div class="flex flex-wrap gap-2">
									{#each tagsByCategory[category] as tag}
										<button
											onclick={() => handleTagClick(tag.name)}
											class="rounded-full border-l-4 bg-gray-200 dark:bg-gray-700 px-2.5 py-1 text-xs text-gray-800 dark:text-gray-200 transition-colors hover:bg-gray-300 dark:hover:bg-gray-600 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 {getCategoryColorClasses(
												category
											)}"
											title="Click to search for this tag"
										>
											{tag.name}
										</button>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</section>
			{/if}

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

