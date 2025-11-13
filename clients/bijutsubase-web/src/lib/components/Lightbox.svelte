<script lang="ts">
	import { getFile, type FileThumb, type FileResponse } from '$lib/api';
	import { fade, fly } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';
	import IconChevronLeft from '~icons/mdi/chevron-left';
	import IconChevronRight from '~icons/mdi/chevron-right';

	let { isOpen = $bindable(false), files = [], currentIndex = $bindable(0) } = $props();

	let fileDetails = $state<FileResponse | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let isVideo = $state(false);

	// Controls visibility state
	let controlsVisible = $state(false);
	// Timer for hiding controls. When a timer not active, this is null.
	let hideTimer: number | null = null;

	// Current file from the array
	let currentFile = $derived(files[currentIndex]);

	// Check if navigation is possible
	let canGoNext = $derived(currentIndex < files.length - 1);
	let canGoPrev = $derived(currentIndex > 0);

	// Fetch file details when current file changes
	$effect(() => {
		if (isOpen && currentFile) {
			loading = true;
			error = null;
			fileDetails = null;

			getFile(currentFile.sha256_hash)
				.then((data) => {
					fileDetails = data;
					// Check if it's a video based on file type
					isVideo = data.file_type.startsWith('video/');
				})
				.catch((err) => {
					error = err instanceof Error ? err.message : 'Failed to load media';
				})
				.finally(() => {
					loading = false;
				});
		}
	});

	function revealControls() {
		controlsVisible = true;
		if (hideTimer !== null) {
			clearTimeout(hideTimer);
		}
		hideTimer = window.setTimeout(() => {
			controlsVisible = false;
			hideTimer = null;
		}, 2000);
	}

	function handleClose() {
		isOpen = false;
		fileDetails = null;
		error = null;
		if (hideTimer !== null) {
			clearTimeout(hideTimer);
			hideTimer = null;
		}
	}

	function goNext() {
		if (canGoNext) {
			currentIndex++;
		}
	}

	function goPrev() {
		if (canGoPrev) {
			currentIndex--;
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		} else if (event.key === 'ArrowRight') {
			goNext();
		} else if (event.key === 'ArrowLeft') {
			goPrev();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		// Close only if clicking the backdrop, not the media
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}

	$effect(() => {
		if (isOpen && typeof window !== 'undefined') {
			// Reset controls visibility when lightbox opens
			controlsVisible = false;

			// Prevent body scroll when lightbox is open
			const originalOverflow = document.body.style.overflow;
			document.body.style.overflow = 'hidden';

			// Add keyboard listeners
			window.addEventListener('keydown', handleKeydown);

			return () => {
				window.removeEventListener('keydown', handleKeydown);
				document.body.style.overflow = originalOverflow;
				// Clear timer on cleanup
				if (hideTimer !== null) {
					clearTimeout(hideTimer);
					hideTimer = null;
				}
			};
		}
	});
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
		transition:fade={{ duration: 200 }}
		onclick={handleBackdropClick}
		onmousemove={revealControls}
		ontouchstart={revealControls}
		role="presentation"
	>
		<!-- Close Button -->
		{#if controlsVisible}
			<button
				in:fly={{ y: -16, x: 16, duration: 200 }}
				out:fade={{ duration: 200 }}
				onclick={handleClose}
				class="absolute right-4 top-4 z-10 rounded-lg bg-black/50 p-2 text-white hover:bg-black/70 focus:outline-none focus:ring-2 focus:ring-white"
				aria-label="Close lightbox"
			>
				<IconClose class="h-8 w-8" />
			</button>
		{/if}

		<!-- Previous Button -->
		{#if canGoPrev && controlsVisible}
			<button
				transition:fade={{ duration: 200 }}
				onclick={goPrev}
				class="absolute left-4 top-1/2 z-10 -translate-y-1/2 rounded-lg bg-black/50 p-2 text-white hover:bg-black/70 focus:outline-none focus:ring-2 focus:ring-white"
				aria-label="Previous image"
			>
				<IconChevronLeft class="h-10 w-10" />
			</button>
		{/if}

		<!-- Next Button -->
		{#if canGoNext && controlsVisible}
			<button
				transition:fade={{ duration: 200 }}
				onclick={goNext}
				class="absolute right-4 top-1/2 z-10 -translate-y-1/2 rounded-lg bg-black/50 p-2 text-white hover:bg-black/70 focus:outline-none focus:ring-2 focus:ring-white"
				aria-label="Next image"
			>
				<IconChevronRight class="h-10 w-10" />
			</button>
		{/if}

		<!-- Media Container -->
		<div
			class="relative flex h-full w-full items-center justify-center"
			transition:fly={{ y: 20, duration: 200 }}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			ontouchstart={revealControls}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			{#if loading}
				<!-- Loading State -->
				<div class="text-center">
					<div class="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-4 border-gray-600 border-t-white"></div>
					<p class="text-white">Loading...</p>
				</div>
			{:else if error}
				<!-- Error State -->
				<div class="rounded-lg bg-red-900/50 p-6 text-center">
					<p class="text-lg text-red-200">Error: {error}</p>
				</div>
			{:else if fileDetails}
				<!-- Media Display -->
				{#if isVideo}
					<video
						src={fileDetails.original_url}
						controls
						autoplay
						class="max-h-[90vh] max-w-[90vw] rounded-lg"
						style="width: auto; height: auto;"
					>
						<track kind="captions" />
					</video>
				{:else}
					<img
						src={fileDetails.original_url}
						alt="Full size media"
						class="max-h-[90vh] max-w-[90vw] rounded-lg object-contain"
						style="width: auto; height: auto;"
					/>
				{/if}
			{/if}
		</div>
	</div>
{/if}

