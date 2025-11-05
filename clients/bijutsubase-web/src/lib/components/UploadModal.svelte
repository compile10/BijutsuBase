<script lang="ts">
	import { uploadFile, type FileResponse } from '$lib/api';
	import { fade, fly } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';

	let { isOpen = $bindable(false) } = $props();

	let selectedFile = $state<File | null>(null);
	let isUploading = $state(false);
	let error = $state<string | null>(null);
	let uploaded = $state<FileResponse | null>(null);
	let fileInputElement: HTMLInputElement | null = $state(null);
	let closeButtonElement: HTMLButtonElement | null = $state(null);
	let modalElement: HTMLDivElement | null = $state(null);

	function handleFileSelect(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target.files && target.files.length > 0) {
			selectedFile = target.files[0];
			error = null;
			uploaded = null;
		}
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
			selectedFile = event.dataTransfer.files[0];
			error = null;
			uploaded = null;
		}
	}

	async function handleUpload() {
		if (!selectedFile) return;

		isUploading = true;
		error = null;

		try {
			uploaded = await uploadFile(selectedFile);
			selectedFile = null;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Upload failed';
		} finally {
			isUploading = false;
		}
	}

	function handleClose() {
		isOpen = false;
		selectedFile = null;
		error = null;
		uploaded = null;
		if (fileInputElement) {
			fileInputElement.value = '';
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		}
	}

	$effect(() => {
		if (isOpen && typeof window !== 'undefined') {
			// Prevent body scroll when modal is open
			const originalOverflow = document.body.style.overflow;
			document.body.style.overflow = 'hidden';

			// Add escape key listener
			window.addEventListener('keydown', handleKeydown);

			// Focus the close button when modal opens
			setTimeout(() => {
				closeButtonElement?.focus();
			}, 100);

			return () => {
				window.removeEventListener('keydown', handleKeydown);
				document.body.style.overflow = originalOverflow;
			};
		}
	});
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
		transition:fade={{ duration: 200 }}
		onclick={handleClose}
		role="presentation"
	>
		<!-- Modal -->
		<div
			bind:this={modalElement}
			class="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-lg bg-white shadow-xl dark:bg-gray-800"
			transition:fly={{ y: 20, duration: 200 }}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => {
				// Stop keyboard events from propagating to backdrop
				e.stopPropagation();
			}}
			role="dialog"
			aria-modal="true"
			aria-labelledby="upload-modal-title"
			tabindex="-1"
		>
			<!-- Header -->
			<div class="flex shrink-0 items-center justify-between border-b border-gray-200 p-6 dark:border-gray-700">
				<h2 id="upload-modal-title" class="text-xl font-semibold text-gray-900 dark:text-white">
					Upload File
				</h2>
				<button
					bind:this={closeButtonElement}
					onclick={handleClose}
					class="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:hover:bg-gray-700 dark:hover:text-gray-300"
					aria-label="Close modal"
				>
					<IconClose class="h-6 w-6" />
				</button>
			</div>

			<!-- Content -->
			<div class="overflow-y-auto p-6">
				{#if uploaded}
					<!-- Success: Show uploaded file details -->
					<div class="space-y-4">
						<div class="text-center">
							<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
								Upload Successful!
							</h3>
							<div class="mx-auto mb-4 max-w-xs">
								<img
									src={uploaded.thumbnail_url}
									alt="Uploaded thumbnail"
									class="mx-auto block rounded-lg border border-gray-200 dark:border-gray-700"
								/>
							</div>
						</div>

						<div class="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
							<div>
								<span class="text-sm font-medium text-gray-600 dark:text-gray-400">SHA256 Hash</span>
								<p class="mt-1 font-mono text-sm text-gray-900 dark:text-white">
									{uploaded.sha256_hash}
								</p>
							</div>

							<div>
								<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Source</span>
								<p class="mt-1 text-sm text-gray-900 dark:text-white">
									{uploaded.source ?? '—'}
								</p>
							</div>

							<div>
								<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Tags</span>
								{#if uploaded.tags.length > 0}
									<div class="mt-2 flex flex-wrap gap-2">
										{#each uploaded.tags as tag}
											<span
												class="rounded-full bg-primary-100 px-3 py-1 text-xs font-medium text-primary-800 dark:bg-primary-900 dark:text-primary-200"
											>
												{tag.name}
											</span>
										{/each}
									</div>
								{:else}
									<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">No tags</p>
								{/if}
							</div>
						</div>

						<div class="flex justify-end">
							<button
								onclick={handleClose}
								class="rounded-lg bg-primary-600 px-6 py-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600"
							>
								Close
							</button>
						</div>
					</div>
				{:else}
					<!-- Upload form -->
					<div class="space-y-4">
						<!-- File input area -->
						<div
							class="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center transition-colors hover:border-primary-400 dark:border-gray-600 dark:hover:border-primary-500"
							ondragover={handleDragOver}
							ondrop={handleDrop}
							role="button"
							tabindex="0"
							onkeydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									fileInputElement?.click();
								}
							}}
						>
							<input
								bind:this={fileInputElement}
								type="file"
								accept="image/*,video/*"
								onchange={handleFileSelect}
								class="hidden"
								id="file-input"
							/>
							<label
								for="file-input"
								class="cursor-pointer text-gray-600 dark:text-gray-400"
							>
								<p class="mb-2 text-sm">
									Drag and drop a file here, or
									<span class="font-semibold text-primary-600 dark:text-primary-400">
										click to browse
									</span>
								</p>
								<p class="text-xs text-gray-500 dark:text-gray-500">
									Supports images and videos
								</p>
							</label>
						</div>

						{#if selectedFile}
							<div class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
								<p class="text-sm text-gray-900 dark:text-white">
									<strong>Selected:</strong> {selectedFile.name}
								</p>
								<p class="mt-1 text-xs text-gray-600 dark:text-gray-400">
									{(selectedFile.size / 1024 / 1024).toFixed(2)} MB
								</p>
							</div>
						{/if}

						{#if error}
							<div
								class="rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
							>
								<p class="text-sm text-red-800 dark:text-red-400">Error: {error}</p>
							</div>
						{/if}

						<div class="flex justify-end gap-3">
							<button
								onclick={handleClose}
								class="rounded-lg border border-gray-300 bg-white px-6 py-2 font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
							>
								Cancel
							</button>
							<button
								onclick={handleUpload}
								disabled={!selectedFile || isUploading}
								class="rounded-lg bg-primary-600 px-6 py-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
							>
								{isUploading ? 'Uploading...' : 'Upload'}
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

