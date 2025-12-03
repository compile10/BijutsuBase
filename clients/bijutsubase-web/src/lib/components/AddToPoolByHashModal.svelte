<script lang="ts">
	import WindowModal from './WindowModal.svelte';
	import IconClose from '~icons/mdi/close';
	import { APIError, addFilesToPool, getFile, type FileResponse, type PoolResponse } from '$lib/api';

	let {
		isOpen = $bindable(false),
		poolId,
		onFilesAdded
	} = $props<{
		isOpen?: boolean;
		poolId: string;
		onFilesAdded?: (pool: PoolResponse) => void;
	}>();

	let sha256 = $state('');
	let previewFile = $state<FileResponse | null>(null);
	let lookupError = $state<string | null>(null);
	let actionError = $state<string | null>(null);
	let isLookingUp = $state(false);
	let isAdding = $state(false);

	function resetState() {
		sha256 = '';
		previewFile = null;
		lookupError = null;
		actionError = null;
		isLookingUp = false;
		isAdding = false;
	}

	function handleClose() {
		isOpen = false;
		resetState();
	}

	function isValidHash(value: string) {
		return /^[a-f0-9]{64}$/i.test(value.trim());
	}

	async function handlePreview(event?: Event) {
		event?.preventDefault();

		const trimmed = sha256.trim().toLowerCase();
		if (!isValidHash(trimmed)) {
			lookupError = 'Enter a 64-character SHA-256 hex string.';
			previewFile = null;
			return;
		}

		isLookingUp = true;
		lookupError = null;
		actionError = null;
		previewFile = null;

		try {
			const file = await getFile(trimmed);
			previewFile = file;
		} catch (err) {
			if (err instanceof APIError && err.status === 404) {
				lookupError = 'No image found for that hash.';
			} else {
				lookupError = err instanceof Error ? err.message : 'Failed to fetch file information.';
			}
		} finally {
			isLookingUp = false;
		}
	}

	async function handleAdd() {
		if (!previewFile) return;

		isAdding = true;
		actionError = null;

		try {
			const updatedPool = await addFilesToPool(poolId, [previewFile.sha256_hash]);
			// TODO: optomize this fetch so tha we dont need to fetch all the pool members
			onFilesAdded?.(updatedPool);
			handleClose();
		} catch (err) {
			actionError =
				err instanceof Error ? err.message : 'Failed to add image to pool.';
		} finally {
			isAdding = false;
		}
	}
</script>

<WindowModal bind:isOpen title="Add by SHA-256" maxWidth="max-w-2xl" onClose={handleClose}>
	<div class="flex items-center justify-between border-b border-gray-200 p-6 dark:border-gray-700">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Add Image by Hash</h2>
		<button
			onclick={handleClose}
			class="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:hover:bg-gray-700 dark:hover:text-gray-300"
			aria-label="Close modal"
		>
			<IconClose class="h-6 w-6" />
		</button>
	</div>

	<form class="space-y-4 p-6" onsubmit={handlePreview}>
		<div>
			<label
				for="pool-hash-input"
				class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
			>
				File SHA-256 <span class="text-red-500">*</span>
			</label>
			<input
				type="text"
				id="pool-hash-input"
				placeholder="64-character hex hash"
				class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
				bind:value={sha256}
				spellcheck="false"
				autocomplete="off"
			/>
			{#if lookupError}
				<p class="mt-2 text-sm text-red-600 dark:text-red-400">{lookupError}</p>
			{/if}
		</div>

		<div class="flex justify-end gap-3">
			<button
				type="button"
				onclick={handleClose}
				class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
			>
				Cancel
			</button>
			<button
				type="submit"
				disabled={isLookingUp}
				class="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
			>
				{isLookingUp ? 'Loading...' : 'Preview'}
			</button>
		</div>

		{#if previewFile}
			<div class="space-y-4 rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
				<div class="flex flex-col gap-4 md:flex-row">
					<div class="shrink-0 overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-600 dark:bg-gray-800">
						<img src={previewFile.thumbnail_url} alt="Preview thumbnail" class="h-40 w-40 object-cover" />
					</div>
					<div class="flex flex-1 flex-col gap-2 text-sm text-gray-700 dark:text-gray-300">
						<div>
							<p class="font-semibold text-gray-900 dark:text-white wrap-break-word">{previewFile.original_filename}</p>
							<p class="font-mono text-xs text-gray-500 dark:text-gray-400 break-all">{previewFile.sha256_hash}</p>
						</div>
						<div class="grid grid-cols-2 gap-2 text-xs">
							<div>
								<p class="text-gray-500 dark:text-gray-400">Type</p>
								<p class="text-gray-900 dark:text-white">{previewFile.file_type.toUpperCase()}</p>
							</div>
							<div>
								<p class="text-gray-500 dark:text-gray-400">Size</p>
								<p class="text-gray-900 dark:text-white">{(previewFile.file_size / 1024 / 1024).toFixed(2)} MB</p>
							</div>
							<div>
								<p class="text-gray-500 dark:text-gray-400">Rating</p>
								<p class="text-gray-900 dark:text-white capitalize">{previewFile.rating}</p>
							</div>
							<div>
								<p class="text-gray-500 dark:text-gray-400">Resolution</p>
								<p class="text-gray-900 dark:text-white">
									{previewFile.width && previewFile.height
										? `${previewFile.width}×${previewFile.height}`
										: '—'}
								</p>
							</div>
						</div>
					</div>
				</div>

				{#if actionError}
					<div class="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
						{actionError}
					</div>
				{/if}

				<div class="flex justify-end">
					<button
						type="button"
						onclick={handleAdd}
						disabled={isAdding}
						class="rounded-lg bg-primary-600 px-5 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
					>
						{isAdding ? 'Adding...' : 'Add to Pool'}
					</button>
				</div>
			</div>
		{/if}
	</form>
</WindowModal>


