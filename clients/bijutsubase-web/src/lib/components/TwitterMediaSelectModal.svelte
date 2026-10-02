<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import type { TwitterMedia, TwitterPost } from '$lib/api';
	import WindowModal from './WindowModal.svelte';
	import IconClose from '~icons/mdi/close';
	import IconCheckCircle from '~icons/mdi/check-circle';
	import IconCircleOutline from '~icons/mdi/checkbox-blank-circle-outline';
	import IconPlay from '~icons/mdi/play-circle-outline';

	let {
		isOpen = $bindable(false),
		post,
		isSubmitting = false,
		onConfirm,
		onCancel
	} = $props<{
		isOpen?: boolean;
		post: TwitterPost | null;
		isSubmitting?: boolean;
		onConfirm: (media: TwitterMedia[]) => void;
		onCancel?: () => void;
	}>();

	// Everything starts selected; most multi-image posts are a set the user wants whole
	const selectedIndexes = $derived(
		new SvelteSet<number>(post?.media.map((media: TwitterMedia) => media.index) ?? [])
	);

	const allSelected = $derived(post !== null && selectedIndexes.size === post.media.length);

	function toggleMedia(index: number) {
		if (selectedIndexes.has(index)) {
			selectedIndexes.delete(index);
		} else {
			selectedIndexes.add(index);
		}
	}

	function toggleAll() {
		if (allSelected) {
			selectedIndexes.clear();
			return;
		}
		for (const media of post?.media ?? []) {
			selectedIndexes.add(media.index);
		}
	}

	function handleConfirm() {
		if (!post) return;
		onConfirm(post.media.filter((media: TwitterMedia) => selectedIndexes.has(media.index)));
	}

	function handleClose() {
		if (isSubmitting) return;
		isOpen = false;
		onCancel?.();
	}
</script>

<WindowModal bind:isOpen title="Select media" maxWidth="max-w-3xl" onClose={handleClose}>
	<div
		class="flex shrink-0 items-center justify-between border-b border-gray-200 p-6 dark:border-gray-700"
	>
		<div class="min-w-0">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Select media</h2>
			{#if post}
				<p class="mt-1 truncate text-sm text-gray-500 dark:text-gray-400">
					{post.author_name} · @{post.author_screen_name}
				</p>
			{/if}
		</div>
		<button
			onclick={handleClose}
			class="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:hover:bg-gray-700 dark:hover:text-gray-300"
			aria-label="Close modal"
		>
			<IconClose class="h-6 w-6" />
		</button>
	</div>

	{#if post}
		<div class="overflow-y-auto p-6">
			<div class="grid grid-cols-2 gap-3">
				{#each post.media as media (media.index)}
					{@const isSelected = selectedIndexes.has(media.index)}
					<button
						type="button"
						onclick={() => toggleMedia(media.index)}
						disabled={isSubmitting}
						aria-pressed={isSelected}
						aria-label="Media {media.index}"
						class="group relative aspect-square overflow-hidden rounded-lg border-2 bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:bg-gray-900 {isSelected
							? 'border-primary-500'
							: 'border-transparent'}"
					>
						<img
							src={media.thumbnail_url}
							alt="Media {media.index}"
							referrerpolicy="no-referrer"
							class="h-full w-full object-cover transition-opacity {isSelected ? '' : 'opacity-50'}"
						/>

						{#if media.type !== 'photo'}
							<div
								class="absolute bottom-2 left-2 flex items-center gap-1 rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white"
							>
								<IconPlay class="h-4 w-4" />
								{media.type === 'video' ? 'Video' : 'GIF'}
							</div>
						{/if}

						{#if media.width && media.height}
							<div
								class="absolute bottom-2 right-2 rounded bg-black/60 px-1.5 py-0.5 text-xs text-white"
							>
								{media.width}×{media.height}
							</div>
						{/if}

						<div class="absolute right-2 top-2">
							{#if isSelected}
								<IconCheckCircle
									class="h-6 w-6 rounded-full bg-white text-primary-600 dark:bg-gray-900 dark:text-primary-400"
								/>
							{:else}
								<IconCircleOutline class="h-6 w-6 text-white drop-shadow-md" />
							{/if}
						</div>
					</button>
				{/each}
			</div>
		</div>

		<div
			class="flex shrink-0 items-center justify-between gap-3 border-t border-gray-200 p-6 dark:border-gray-700"
		>
			<button
				onclick={toggleAll}
				disabled={isSubmitting}
				class="text-sm font-medium text-primary-600 hover:underline disabled:opacity-50 dark:text-primary-400"
			>
				{allSelected ? 'Deselect all' : 'Select all'}
			</button>
			<div class="flex gap-3">
				<button
					onclick={handleClose}
					disabled={isSubmitting}
					class="rounded-lg border border-gray-300 bg-white px-6 py-2 font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
				>
					Cancel
				</button>
				<button
					onclick={handleConfirm}
					disabled={selectedIndexes.size === 0 || isSubmitting}
					class="rounded-lg bg-primary-600 px-6 py-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
				>
					{isSubmitting ? 'Uploading...' : `Upload ${selectedIndexes.size}`}
				</button>
			</div>
		</div>
	{/if}
</WindowModal>
