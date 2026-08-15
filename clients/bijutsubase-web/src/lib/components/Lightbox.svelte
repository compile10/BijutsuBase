<script lang="ts">
	import { getFile, type FileThumb, type FileResponse } from '$lib/api';
	import { fade, fly } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';
	import IconChevronLeft from '~icons/mdi/chevron-left';
	import IconChevronRight from '~icons/mdi/chevron-right';
	import IconInformation from '~icons/mdi/information-outline';
	import InfoPanel from './InfoPanel.svelte';
	import AddChildByHashModal from './AddChildByHashModal.svelte';

	let { isOpen = $bindable(false), files = [], currentIndex = $bindable(0) } = $props();

	let fileDetails = $state<FileResponse | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let isVideo = $state(false);
	let infoOpen = $state(false);
	let ephemeralSha = $state<string | null>(null);
	let isAddChildModalOpen = $state(false);

	// Controls visibility state
	let controlsVisible = $state(false);
	// Timer for hiding controls. When a timer not active, this is null.
	let hideTimer: number | null = null;

	let dialogEl = $state<HTMLDialogElement | null>(null);
	let closing = $state(false);
	const EXIT_DURATION = 200;

	// Touch gesture tracking
	let touchStartX = $state<number | null>(null);
	let touchStartY = $state<number | null>(null);
	let touchStartTime = $state<number | null>(null);

	// Current file from the array
	let currentFile = $derived(files[currentIndex]);
	let activeSha = $derived(ephemeralSha ?? currentFile?.sha256_hash);

	// Check if navigation is possible
	let canGoNext = $derived(ephemeralSha === null && currentIndex < files.length - 1);
	let canGoPrev = $derived(ephemeralSha === null && currentIndex > 0);

	// Fetch file details when current file changes
	$effect(() => {
		if (isOpen && activeSha) {
			loading = true;
			error = null;
			fileDetails = null;

			getFile(activeSha)
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

	function toggleControls() {
		if (controlsVisible) {
			controlsVisible = false;
			if (hideTimer !== null) {
				clearTimeout(hideTimer);
				hideTimer = null;
			}
		} else {
			revealControls();
		}
	}

	function handleClose() {
		isOpen = false;
		fileDetails = null;
		error = null;
		infoOpen = false;
		ephemeralSha = null;
		if (hideTimer !== null) {
			clearTimeout(hideTimer);
			hideTimer = null;
		}
	}

	function goNext() {
		if (canGoNext) {
			ephemeralSha = null;
			currentIndex++;
		}
	}

	function goPrev() {
		if (canGoPrev) {
			ephemeralSha = null;
			currentIndex--;
		}
	}

	function openBySha(sha256: string) {
		const index = files.findIndex((f: FileThumb) => f.sha256_hash === sha256);
		if (index >= 0) {
			ephemeralSha = null;
			currentIndex = index;
			return;
		}

		// Ephemeral mode: open this file even if it's not in the current list.
		ephemeralSha = sha256;
	}

	// WindowModal renders a plain div rather than a nested <dialog>, so a modal stacked on
	// the lightbox does not take the keyboard from it. Detect any of them by marker.
	function modalIsStacked() {
		return document.querySelector('[data-window-modal]') !== null;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (modalIsStacked()) return;

		// This listener is on window, so it also fires while typing in the info panel.
		const target = event.target as HTMLElement | null;
		if (target?.closest('input, textarea, select, [contenteditable]')) return;

		if (event.key === 'ArrowRight') {
			goNext();
		} else if (event.key === 'ArrowLeft') {
			goPrev();
		}
	}

	function handleCancel(event: Event) {
		// Default cancel drops the dialog from the top layer at once, skipping the fade.
		// A stacked modal handles its own Escape, so the lightbox stays open behind it.
		event.preventDefault();
		if (!modalIsStacked()) {
			handleClose();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		// Close only if clicking the backdrop, not the media
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}

	// Touch gesture constants
	const SWIPE_THRESHOLD = 50; // pixels
	const TAP_THRESHOLD = 10; // pixels
	const TAP_MAX_DURATION = 300; // ms

	function handleTouchStart(event: TouchEvent) {
		const touch = event.touches[0];
		touchStartX = touch.clientX;
		touchStartY = touch.clientY;
		touchStartTime = Date.now();
	}

	function handleTouchMove(event: TouchEvent) {
		if (touchStartX === null || touchStartY === null) return;

		const touch = event.touches[0];
		const deltaX = Math.abs(touch.clientX - touchStartX);
		const deltaY = Math.abs(touch.clientY - touchStartY);

		// If horizontal movement is dominant, prevent vertical scroll
		if (deltaX > deltaY && deltaX > 10) {
			event.preventDefault();
		}
	}

	function handleTouchEnd(event: TouchEvent) {
		if (touchStartX === null || touchStartY === null) return;

		const target = event.target as HTMLElement;
		const touch = event.changedTouches[0];
		const deltaX = touch.clientX - touchStartX;
		const deltaY = touch.clientY - touchStartY;
		const duration = Date.now() - (touchStartTime ?? 0);

		const absX = Math.abs(deltaX);
		const absY = Math.abs(deltaY);

		const isHorizontalSwipe = absX > SWIPE_THRESHOLD && absX > absY;
		const isOnVideo = target.closest('video') !== null;

		// For videos: only handle horizontal swipes, let taps pass through for video controls
		if (isOnVideo) {
			if (isHorizontalSwipe) {
				if (deltaX > 0) {
					goPrev();
				} else {
					goNext();
				}
				event.preventDefault();
			}
			// Reset touch state and let non-swipe gestures pass through to video
			touchStartX = null;
			touchStartY = null;
			touchStartTime = null;
			return;
		}

		// Don't handle touches on other interactive elements (let them handle their own clicks)
		if (target.closest('button') || target.closest('[data-info-panel]')) {
			touchStartX = null;
			touchStartY = null;
			touchStartTime = null;
			return;
		}

		if (isHorizontalSwipe) {
			// Horizontal swipe
			if (deltaX > 0) {
				goPrev();
			} else {
				goNext();
			}
		} else if (absX < TAP_THRESHOLD && absY < TAP_THRESHOLD && duration < TAP_MAX_DURATION) {
			// Tap - toggle controls
			toggleControls();
		}

		// Prevent synthetic mouse events (mousemove would trigger revealControls)
		event.preventDefault();

		// Reset touch state
		touchStartX = null;
		touchStartY = null;
		touchStartTime = null;
	}

	// Keep the dialog in sync with isOpen, delaying close() so the fade can finish.
	$effect(() => {
		const el = dialogEl;
		if (!el) return;

		if (isOpen) {
			// Reopening mid-fade cancels the pending close.
			closing = false;
			if (!el.open) el.showModal();
			return;
		}

		if (!el.open) return;

		// Safari and Firefox cannot transition `overlay`, so close() would drop the dialog
		// out of the top layer before the fade renders.
		closing = true;
		const timer = window.setTimeout(() => {
			closing = false;
			el.close();
		}, EXIT_DURATION);

		return () => window.clearTimeout(timer);
	});

	$effect(() => {
		if (isOpen && typeof window !== 'undefined') {
			// Reset controls visibility when lightbox opens
			controlsVisible = false;

			window.addEventListener('keydown', handleKeydown);

			return () => {
				window.removeEventListener('keydown', handleKeydown);
				// Clear timer on cleanup
				if (hideTimer !== null) {
					clearTimeout(hideTimer);
					hideTimer = null;
				}
			};
		}
	});
</script>

<!-- The overlay is the UA's ::backdrop, which covers the viewport with no author geometry to round short of it. -->
<dialog
	bind:this={dialogEl}
	data-lightbox
	class="fixed inset-0 hidden h-full max-h-none w-full max-w-none overflow-hidden bg-transparent open:block"
	class:closing
	onclose={handleClose}
	oncancel={handleCancel}
	onclick={handleBackdropClick}
	onmousemove={revealControls}
	ontouchstart={handleTouchStart}
	ontouchmove={handleTouchMove}
	ontouchend={handleTouchEnd}
>
	{#if isOpen}
		<!-- Everything sits in the safe rectangle; the backdrop behind it still covers the screen. -->
		<div
			class="absolute inset-safe flex items-center justify-center p-4"
			onclick={handleBackdropClick}
			role="presentation"
		>
			<!-- Info and Close Buttons -->
			{#if controlsVisible}
				<div class="absolute right-4 top-4 z-10 flex gap-2">
					<button
						in:fly={{ y: -16, x: 16, duration: 200 }}
						out:fade={{ duration: 200 }}
						onclick={() => (infoOpen = !infoOpen)}
						class="rounded-lg bg-black/50 p-2 text-white hover:bg-black/70 focus:outline-none focus:ring-2 focus:ring-white"
						aria-label="Toggle info panel"
					>
						<IconInformation class="h-8 w-8" />
					</button>
					<button
						in:fly={{ y: -16, x: 16, duration: 200 }}
						out:fade={{ duration: 200 }}
						onclick={handleClose}
						class="rounded-lg bg-black/50 p-2 text-white hover:bg-black/70 focus:outline-none focus:ring-2 focus:ring-white"
						aria-label="Close lightbox"
					>
						<IconClose class="h-8 w-8" />
					</button>
				</div>
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
				class="pointer-events-none relative flex h-full w-full items-center justify-center"
				transition:fly={{ y: 20, duration: 200 }}
			>
				{#if loading}
					<!-- Loading State -->
					<div class="text-center">
						<div
							class="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-4 border-gray-600 border-t-white"
						></div>
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
							class="pointer-events-auto max-h-full max-w-full rounded-lg object-contain"
						>
							<track kind="captions" />
						</video>
					{:else}
						<img
							src={fileDetails.original_url}
							alt="Full size media"
							class="pointer-events-auto max-h-full max-w-full rounded-lg object-contain"
						/>
					{/if}
				{/if}
			</div>
		</div>

		<!-- Full-bleed surfaces sit outside the safe box and inset their own contents instead. -->
		{#if fileDetails}
			<InfoPanel
				bind:open={infoOpen}
				bind:file={fileDetails}
				onNavigateToFile={openBySha}
				onOpenAddChildModal={() => (isAddChildModalOpen = true)}
			/>
		{/if}

		<!-- Must be inside the dialog: the top layer paints above the document, so anything outside it is hidden and inert. -->
		{#if fileDetails?.family_id && isAddChildModalOpen}
			<AddChildByHashModal
				bind:isOpen={isAddChildModalOpen}
				familyId={fileDetails.family_id}
				onChildAdded={(family) => {
					// We already have the updated family payload; patch the bound file state instead of refetching.
					if (fileDetails && fileDetails.sha256_hash === family.parent_sha256_hash) {
						fileDetails = {
							...fileDetails,
							family_id: family.id,
							children: family.children
						};
					}
				}}
			/>
		{/if}
	{/if}
</dialog>

<style>
	:global {
		/* Literal color: iOS Safari dr ops custom properties in ::backdrop, rendering it transparent. */
		dialog[data-lightbox]::backdrop {
			background-color: rgb(0 0 0 / 0.95);
		}

		dialog[data-lightbox],
		dialog[data-lightbox]::backdrop {
			opacity: 0;
			transition: opacity 200ms;
		}

		dialog[data-lightbox][open],
		dialog[data-lightbox][open]::backdrop {
			opacity: 1;
		}

		dialog[data-lightbox][open].closing,
		dialog[data-lightbox][open].closing::backdrop {
			opacity: 0;
		}

		/* Without this the entry transition never runs, since the dialog starts at display: none. */
		@starting-style {
			dialog[data-lightbox][open],
			dialog[data-lightbox][open]::backdrop {
				opacity: 0; 
			}
		}
	}
</style>
