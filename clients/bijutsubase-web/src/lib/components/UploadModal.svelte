<script lang="ts">
	import { onDestroy } from 'svelte';
	import { uploadFile, uploadByUrl, type FileResponse } from '$lib/api';
	import { processTagSource, createProcessingPoller } from '$lib/utils';
	import WindowModal from './WindowModal.svelte';
	import TagSection from './TagSection.svelte';
	import IconClose from '~icons/mdi/close';

	let { isOpen = $bindable(false) } = $props();

	let selectedFile = $state<File | null>(null);
	let isUploading = $state(false);
	let isProcessing = $state(false);
	let error = $state<string | null>(null);
	let uploaded = $state<FileResponse | null>(null);
	let fileInputElement: HTMLInputElement | null = $state(null);
	let mode = $state<'url' | 'file'>('url');
	let urlString = $state('');

	// Create polling controller
	const poller = createProcessingPoller((result) => {
		uploaded = result.file;
		if (result.status === 'completed' || result.status === 'failed') {
			isProcessing = false;
		}
		if (result.error) {
			error = result.error;
		}
	});

	// Cleanup polling on component destroy
	onDestroy(() => {
		poller.stop();
	});

	async function handleUploadComplete(result: FileResponse) {
		uploaded = result;
		
		// Check if processing is still pending/in-progress
		if (result.processing_status !== 'completed' && result.processing_status !== 'failed') {
			isProcessing = true;
			poller.start(result.sha256_hash);
		} else if (result.processing_status === 'failed') {
			error = result.processing_error || 'Processing failed';
		}
	}

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
			const result = await uploadFile(selectedFile);
			selectedFile = null;
			await handleUploadComplete(result);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Upload failed';
		} finally {
			isUploading = false;
		}
	}

	async function handleUploadUrl() {
		if (!urlString) return;
		isUploading = true;
		error = null;
		try {
			const result = await uploadByUrl(urlString);
			urlString = '';
			await handleUploadComplete(result);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Upload failed';
		} finally {
			isUploading = false;
		}
	}

	function handleClose() {
		poller.stop();
		isOpen = false;
		selectedFile = null;
		error = null;
		uploaded = null;
		isProcessing = false;
		if (fileInputElement) {
			fileInputElement.value = '';
		}
	}
</script>

<WindowModal bind:isOpen title="Upload" maxWidth="max-w-2xl" onClose={handleClose}>
	<!-- Header -->
	<div class="flex shrink-0 items-center justify-between border-b border-gray-200 p-6 dark:border-gray-700">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
			Upload
		</h2>
		<button
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
						{#if isProcessing}
							Processing Video...
						{:else if uploaded.processing_status === 'failed'}
							Processing Failed
						{:else}
							Upload Successful!
						{/if}
					</h3>
					<div class="mx-auto mb-4 max-w-xs">
						{#if uploaded.thumbnail_url}
							<img
								src={uploaded.thumbnail_url}
								alt="Uploaded thumbnail"
								class="mx-auto block rounded-lg border border-gray-200 dark:border-gray-700"
							/>
						{:else if isProcessing}
							<!-- Placeholder while processing -->
							<div class="mx-auto flex h-48 w-48 items-center justify-center rounded-lg border border-gray-200 bg-gray-100 dark:border-gray-700 dark:bg-gray-800">
								<div class="text-center">
									<svg class="mx-auto h-12 w-12 animate-spin text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
										Generating thumbnail...
									</p>
								</div>
							</div>
						{:else}
							<!-- No thumbnail available -->
							<div class="mx-auto flex h-48 w-48 items-center justify-center rounded-lg border border-gray-200 bg-gray-100 dark:border-gray-700 dark:bg-gray-800">
								<span class="text-gray-400">No thumbnail</span>
							</div>
						{/if}
					</div>
				</div>

				{#if isProcessing}
					<!-- Processing status indicator -->
					<div class="rounded-lg border border-blue-300 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
						<p class="text-sm text-blue-800 dark:text-blue-400">
							Your video is being processed. This may take a few minutes for large files.
							The thumbnail and tags will appear when processing is complete.
						</p>
					</div>
				{/if}

				<div class="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
					<div>
						<span class="text-sm font-medium text-gray-600 dark:text-gray-400">SHA256 Hash</span>
						<p class="mt-1 font-mono text-sm text-gray-900 dark:text-white">
							{uploaded.sha256_hash}
						</p>
					</div>

					{#if !isProcessing}
						<div>
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Source</span>
							<p class="mt-1 text-sm text-gray-900 dark:text-white">
								{uploaded.source ?? '—'}
							</p>
						</div>

						<div>
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Tag Source</span>
							<p class="mt-1 text-sm text-gray-900 dark:text-white">
								{processTagSource(uploaded.tag_source)}
							</p>
						</div>

						<div>
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400">AI Generated</span>
							<p class="mt-1 text-sm text-gray-900 dark:text-white">
								{uploaded.ai_generated ? 'Yes' : 'No'}
							</p>
						</div>
					{:else}
						<div>
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Status</span>
							<p class="mt-1 text-sm text-gray-900 dark:text-white">
								{uploaded.processing_status === 'pending' ? 'Waiting to process...' : 'Processing...'}
							</p>
						</div>
					{/if}
				</div>

				<!-- Tags Section (only show when processing is complete) -->
				{#if !isProcessing && uploaded.processing_status === 'completed'}
					<div class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
						<TagSection bind:file={uploaded} />
					</div>
				{/if}

				<div class="flex justify-end">
					<button
						onclick={handleClose}
						class="rounded-lg bg-primary-600 px-6 py-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600"
					>
						{isProcessing ? 'Close (processing continues)' : 'Close'}
					</button>
				</div>
			</div>
		{:else}
			<!-- Upload form -->
			<div class="space-y-4">
				<!-- Mode toggle -->
				<div class="flex items-center gap-2">
					<button
						onclick={() => (mode = 'url')}
						class="rounded-lg px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-400 {mode === 'url' ? 'bg-primary-600 text-white dark:bg-primary-500' : 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'}"
					>
						URL
					</button>
					<button
						onclick={() => (mode = 'file')}
						class="rounded-lg px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-400 {mode === 'file' ? 'bg-primary-600 text-white dark:bg-primary-500' : 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'}"
					>
						File
					</button>
				</div>

				{#if mode === 'url'}
					<!-- URL mode content -->
					<div class="flex items-center gap-3">
						<input
							type="url"
							placeholder="https://examplebooru.com/image-or-video"
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder:text-gray-500"
							bind:value={urlString}
							spellcheck="false"
							autocomplete="off"
						/>
					</div>
				{:else}
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
				{/if}

				{#if error}
					<div
						class="rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
					>
						<p class="text-sm text-red-800 dark:text-red-400">Error: {error}</p>
					</div>
				{/if}

				<!-- Action buttons -->
				<div class="flex justify-end gap-3">
					<button
						onclick={handleClose}
						class="rounded-lg border border-gray-300 bg-white px-6 py-2 font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
					>
						Cancel
					</button>
					<button
						onclick={mode === 'url' ? handleUploadUrl : handleUpload}
						disabled={(mode === 'url' ? !urlString : !selectedFile) || isUploading}
						class="rounded-lg bg-primary-600 px-6 py-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
					>
						{isUploading ? 'Uploading...' : 'Upload'}
					</button>
				</div>
			</div>
		{/if}
	</div>
</WindowModal>
