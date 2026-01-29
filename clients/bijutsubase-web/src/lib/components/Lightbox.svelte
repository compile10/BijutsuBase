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

		// Don't handle touches on interactive elements (let them handle their own clicks)
		const target = event.target as HTMLElement;
		if (target.closest('button') || target.closest('video') || target.closest('[data-info-panel]')) {
			touchStartX = null;
			touchStartY = null;
			touchStartTime = null;
			return;
		}

		const touch = event.changedTouches[0];
		const deltaX = touch.clientX - touchStartX;
		const deltaY = touch.clientY - touchStartY;
		const duration = Date.now() - (touchStartTime ?? 0);

		const absX = Math.abs(deltaX);
		const absY = Math.abs(deltaY);

		if (absX > SWIPE_THRESHOLD && absX > absY) {
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
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/95 p-4"
		transition:fade={{ duration: 200 }}
		onclick={handleBackdropClick}
		onmousemove={revealControls}
		ontouchstart={handleTouchStart}
		ontouchmove={handleTouchMove}
		ontouchend={handleTouchEnd}
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
			class="relative flex h-full w-full items-center justify-center"
			transition:fly={{ y: 20, duration: 200 }}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			ontouchstart={handleTouchStart}
			ontouchmove={handleTouchMove}
			ontouchend={handleTouchEnd}
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

		<!-- Info Panel -->
		{#if fileDetails}
			<InfoPanel bind:open={infoOpen} bind:file={fileDetails} onNavigateToFile={openBySha} bind:isAddChildModalOpen />
		{/if}
	</div>
{/if}

<!-- Add Child Modal - rendered outside the Lightbox stacking context -->
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

