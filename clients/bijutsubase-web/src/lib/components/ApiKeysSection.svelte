<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import {
		addDays,
		addMinutes,
		addYears,
		differenceInDays,
		format,
		formatDistanceToNow,
		isFuture,
		isPast,
		isValid,
		parseISO
	} from 'date-fns';
	import {
		createApiKey,
		deleteApiKey,
		listApiKeys,
		type ApiKeyResponse,
		type CreateApiKeyResponse
	} from '$lib/api';
	import IconPlus from '~icons/mdi/plus';
	import IconContentCopy from '~icons/mdi/content-copy';
	import IconCheck from '~icons/mdi/check';
	import IconDeleteOutline from '~icons/mdi/delete-outline';
	import IconAlertOutline from '~icons/mdi/alert-outline';
	import IconKeyVariant from '~icons/mdi/key-variant';

	let { onBusyChange }: { onBusyChange?: (busy: boolean) => void } = $props();

	const PAGE_SIZE = 10;

	type ExpiryPreset = 'never' | '30d' | '90d' | '1y' | 'custom';
	type PageToken = number | 'ellipsis';

	// List & pagination state
	let items = $state<ApiKeyResponse[]>([]);
	let total = $state(0);
	let currentPage = $state(1);
	let isLoading = $state(true);
	let loadError = $state<string | null>(null);
	let actionError = $state<string | null>(null);

	// Create form state
	let isCreateOpen = $state(false);
	let keyName = $state('');
	let expiryPreset = $state<ExpiryPreset>('never');
	let customExpiry = $state('');
	let formError = $state<string | null>(null);
	let isSubmitting = $state(false);

	// One-time secret reveal state (cleared on dismiss or unmount)
	let createdKey = $state<CreateApiKeyResponse | null>(null);
	let copied = $state(false);
	let copyError = $state<string | null>(null);
	let copyTimer: ReturnType<typeof setTimeout> | null = null;

	// Delete confirmation state
	let confirmingDeleteId = $state<string | null>(null);
	let deletingId = $state<string | null>(null);

	let fetchController: AbortController | null = null;

	let totalPages = $derived(Math.max(1, Math.ceil(total / PAGE_SIZE)));
	let rangeStart = $derived(total === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1);
	let rangeEnd = $derived(Math.min(currentPage * PAGE_SIZE, total));
	let visiblePages = $derived(buildVisiblePages(currentPage, totalPages));

	$effect(() => {
		onBusyChange?.(isSubmitting || deletingId !== null);
	});

	/**
	 * Build pagination tokens for the current page.
	 *
	 * Rules (when pages > 7; otherwise all pages are shown):
	 * - Always include the first page (1), the last page (`pages`), and the current page with its
	 *   two immediate neighbors (`current - 1` and `current + 1`).
	 * - At the start/end, an out-of-bounds neighbor simply drops off rather than extending the
	 *   window in the other direction (so `current = 1` shows `1, 2, ..., pages`).
	 * - Whenever the `[current - 1, current + 1]` window is disconnected from `1` or `pages`,
	 *   fill that gap with an ellipsis.
	 */
	function buildVisiblePages(current: number, pages: number): PageToken[] {
		if (pages <= 7) {
			return Array.from({ length: pages }, (_, i) => i + 1);
		}

		// Adds the first page
		const tokens: PageToken[] = [1];

		//Builds the neighbor window
		const start = Math.max(2, current - 1);
		const end = Math.min(pages - 1, current + 1);

		if (start > 2) {
			tokens.push('ellipsis');
		}
		for (let p = start; p <= end; p++) {
			tokens.push(p);
		}
		if (end < pages - 1) {
			tokens.push('ellipsis');
		}

		// Adds the last page
		tokens.push(pages);
		return tokens;
	}

	function formatDate(iso: string): string {
		const date = parseISO(iso);
		if (!isValid(date)) {
			console.error('Invalid API key date string:', iso);
			return 'Invalid date';
		}
		return format(date, 'MMM d, yyyy');
	}

	function formatLastUsed(iso: string | null): string {
		if (!iso) return 'Never used';
		const date = parseISO(iso);
		if (!isValid(date)) {
			console.error('Invalid API key last_used_at string:', iso);
			return 'Unknown';
		}
		if (differenceInDays(new Date(), date) >= 7) {
			return format(date, 'MMM d, yyyy');
		}
		return formatDistanceToNow(date, { addSuffix: true });
	}

	function isExpired(key: ApiKeyResponse): boolean {
		if (!key.expires_at) return false;
		const date = parseISO(key.expires_at);
		return isValid(date) && isPast(date);
	}

	function getMinCustomDateTime(): string {
		return format(addMinutes(new Date(), 1), "yyyy-MM-dd'T'HH:mm");
	}

	async function fetchKeys(page: number) {
		fetchController?.abort();
		const controller = new AbortController();
		fetchController = controller;

		isLoading = true;
		loadError = null;

		try {
			const res = await listApiKeys(page, PAGE_SIZE, controller.signal);
			items = res.items;
			total = res.total;
			currentPage = res.page;
		} catch (err) {
			if (controller.signal.aborted) return;
			loadError = err instanceof Error ? err.message : 'Failed to load API keys';
		} finally {
			if (fetchController === controller) {
				fetchController = null;
				isLoading = false;
			}
		}
	}

	function openCreateForm() {
		actionError = null;
		formError = null;
		confirmingDeleteId = null;
		isCreateOpen = true;
	}

	function closeCreateForm() {
		isCreateOpen = false;
		keyName = '';
		expiryPreset = 'never';
		customExpiry = '';
		formError = null;
	}

	function resolveExpiresAt(): { value: string | null; error?: string } {
		if (expiryPreset === 'never') {
			return { value: null };
		}

		const now = new Date();
		if (expiryPreset === '30d') {
			return { value: addDays(now, 30).toISOString() };
		}
		if (expiryPreset === '90d') {
			return { value: addDays(now, 90).toISOString() };
		}
		if (expiryPreset === '1y') {
			return { value: addYears(now, 1).toISOString() };
		}

		if (!customExpiry) {
			return { value: null, error: 'Please choose an expiration date and time.' };
		}
		const parsed = parseISO(customExpiry);
		if (!isValid(parsed) || !isFuture(parsed)) {
			return { value: null, error: 'Expiration date must be in the future.' };
		}
		return { value: parsed.toISOString() };
	}

	async function handleCreateSubmit(event: Event) {
		event.preventDefault();
		formError = null;
		actionError = null;

		const trimmedName = keyName.trim();
		if (!trimmedName) {
			formError = 'Please enter a name for this API key.';
			return;
		}

		const expiry = resolveExpiresAt();
		if (expiry.error) {
			formError = expiry.error;
			return;
		}

		isSubmitting = true;
		try {
			const created = await createApiKey(trimmedName, expiry.value);
			createdKey = created;
			copied = false;
			copyError = null;
			closeCreateForm();
			await fetchKeys(1);
		} catch (err) {
			formError = err instanceof Error ? err.message : 'Failed to create API key';
		} finally {
			isSubmitting = false;
		}
	}

	async function handleCopyRawKey() {
		if (!createdKey) return;
		copyError = null;

		try {
			if (navigator.clipboard?.writeText) {
				await navigator.clipboard.writeText(createdKey.api_key);
			} else {
				const textarea = document.createElement('textarea');
				textarea.value = createdKey.api_key;
				textarea.style.position = 'fixed';
				textarea.style.opacity = '0';
				document.body.appendChild(textarea);
				textarea.select();
				const ok = document.execCommand('copy');
				document.body.removeChild(textarea);
				if (!ok) throw new Error('Clipboard copy failed');
			}

			copied = true;
			if (copyTimer) clearTimeout(copyTimer);
			copyTimer = setTimeout(() => {
				copied = false;
				copyTimer = null;
			}, 2500);
		} catch {
			copyError = 'Could not copy automatically. Select the key above and copy it manually.';
		}
	}

	function dismissCreatedKey() {
		createdKey = null;
		copied = false;
		copyError = null;
		if (copyTimer) {
			clearTimeout(copyTimer);
			copyTimer = null;
		}
	}

	async function handleConfirmDelete(apiKeyId: string) {
		actionError = null;
		deletingId = apiKeyId;

		try {
			await deleteApiKey(apiKeyId);
			confirmingDeleteId = null;

			if (createdKey?.id === apiKeyId) {
				dismissCreatedKey();
			}

			const nextPage = items.length <= 1 && currentPage > 1 ? currentPage - 1 : currentPage;
			await fetchKeys(nextPage);
		} catch (err) {
			actionError = err instanceof Error ? err.message : 'Failed to delete API key';
		} finally {
			deletingId = null;
		}
	}

	function goToPage(page: number) {
		if (page < 1 || page > totalPages || page === currentPage || isLoading) return;
		confirmingDeleteId = null;
		actionError = null;
		fetchKeys(page);
	}

	onMount(() => {
		fetchKeys(1);
	});

	onDestroy(() => {
		fetchController?.abort();
		// Ensure the raw API key never lingers in memory after navigating away or closing Settings
		onBusyChange?.(false);
		dismissCreatedKey();
	});
</script>

<div class="space-y-4">
	<!-- Section Header -->
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white">API Keys</h3>
			<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
				Create personal API keys to authenticate scripts, CLI tools, or external apps with your
				account.
			</p>
		</div>

		<button
			type="button"
			onclick={openCreateForm}
			disabled={isCreateOpen}
			class="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
		>
			<IconPlus class="h-4 w-4" />
			Create API Key
		</button>
	</div>

	<!-- Inline Create Form -->
	{#if isCreateOpen}
		<div
			class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50"
		>
			<div class="mb-3 flex items-center justify-between gap-2">
				<h4 class="text-sm font-semibold text-gray-900 dark:text-white">New API Key</h4>
				<button
					type="button"
					onclick={closeCreateForm}
					disabled={isSubmitting}
					class="rounded-md px-2 py-1 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-200 hover:text-gray-900 disabled:opacity-50 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
				>
					Cancel
				</button>
			</div>

			<form onsubmit={handleCreateSubmit} class="space-y-3" novalidate>
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<div>
						<label
							for="api-key-name"
							class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300"
						>
							Name <span class="text-red-500">*</span>
						</label>
						<input
							id="api-key-name"
							type="text"
							bind:value={keyName}
							maxlength={100}
							required
							disabled={isSubmitting}
							placeholder="e.g., Desktop CLI, Upload Script"
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500 dark:focus:border-primary-400 dark:focus:ring-primary-400"
						/>
					</div>

					<div>
						<label
							for="api-key-expiry"
							class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300"
						>
							Expiration
						</label>
						<select
							id="api-key-expiry"
							bind:value={expiryPreset}
							disabled={isSubmitting}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:focus:border-primary-400 dark:focus:ring-primary-400"
						>
							<option value="never">Never expires</option>
							<option value="30d">30 days</option>
							<option value="90d">90 days</option>
							<option value="1y">1 year</option>
							<option value="custom">Custom date...</option>
						</select>
					</div>
				</div>

				{#if expiryPreset === 'custom'}
					<div>
						<label
							for="api-key-custom-expiry"
							class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300"
						>
							Expiration Date <span class="text-red-500">*</span>
						</label>
						<input
							id="api-key-custom-expiry"
							type="datetime-local"
							bind:value={customExpiry}
							min={getMinCustomDateTime()}
							required
							disabled={isSubmitting}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:focus:border-primary-400 dark:focus:ring-primary-400"
						/>
					</div>
				{/if}

				{#if formError}
					<p class="text-sm text-red-600 dark:text-red-400">{formError}</p>
				{/if}

				<div class="flex justify-end gap-2 border-t border-gray-200 pt-3 dark:border-gray-700">
					<button
						type="button"
						onclick={closeCreateForm}
						disabled={isSubmitting}
						class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
					>
						Cancel
					</button>
					<button
						type="submit"
						disabled={isSubmitting || !keyName.trim()}
						class="rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
					>
						{isSubmitting ? 'Creating...' : 'Generate Key'}
					</button>
				</div>
			</form>
		</div>
	{/if}

	<!-- One-Time Raw API Key Reveal Banner -->
	{#if createdKey}
		<div
			role="alert"
			class="rounded-lg border border-amber-400 bg-amber-50 p-4 dark:border-amber-500/70 dark:bg-amber-950/35"
		>
			<div class="mb-3 flex items-start gap-2.5">
				<IconAlertOutline class="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
				<div class="min-w-0 flex-1">
					<p class="text-sm font-semibold text-amber-950 dark:text-amber-100">
						Copy your new API key now — "{createdKey.name}"
					</p>
					<p class="mt-0.5 text-xs text-amber-800 dark:text-amber-200/90">
						For your security, this raw API key is only shown once. It will disappear permanently as
						soon as you dismiss this notice, close Settings, or navigate away.
					</p>
				</div>
			</div>

			<div class="flex flex-col gap-2 sm:flex-row sm:items-stretch">
				<div
					class="flex min-w-0 flex-1 items-center overflow-x-auto whitespace-nowrap rounded-lg border border-amber-300 bg-white px-3 py-2 font-mono text-xs text-gray-900 select-all dark:border-amber-700/70 dark:bg-gray-900 dark:text-gray-100"
				>
					{createdKey.api_key}
				</div>
				<button
					type="button"
					onclick={handleCopyRawKey}
					class="inline-flex shrink-0 items-center justify-center gap-1.5 rounded-lg bg-primary-600 px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-600"
				>
					{#if copied}
						<IconCheck class="h-4 w-4" />
						Copied!
					{:else}
						<IconContentCopy class="h-4 w-4" />
						Copy Key
					{/if}
				</button>
			</div>

			{#if copyError}
				<p class="mt-2 text-xs text-red-600 dark:text-red-400">{copyError}</p>
			{/if}

			<div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs">
				<span class="text-amber-800 dark:text-amber-200/80">
					{#if copied}
						<span class="font-semibold text-emerald-700 dark:text-emerald-400">
							Copied to clipboard.
						</span>
						Store it somewhere safe before closing.
					{:else}
						Send as <code class="rounded bg-black/5 px-1 py-0.5 dark:bg-white/10"
							>Authorization: Bearer &lt;key&gt;</code
						>
					{/if}
				</span>
				<button
					type="button"
					onclick={dismissCreatedKey}
					class="rounded-md border border-amber-300 bg-white px-2.5 py-1 text-xs font-medium text-amber-900 transition-colors hover:bg-amber-100 dark:border-amber-700 dark:bg-gray-800 dark:text-amber-100 dark:hover:bg-gray-700"
				>
					I've copied it
				</button>
			</div>
		</div>
	{/if}

	{#if actionError}
		<div
			class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
		>
			{actionError}
		</div>
	{/if}

	<!-- Table Container -->
	<div class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900/40">
		{#if isLoading && items.length === 0}
			<div class="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
				Loading API keys...
			</div>
		{:else if loadError && items.length === 0}
			<div class="p-6 text-center">
				<p class="text-sm text-red-600 dark:text-red-400">{loadError}</p>
				<button
					type="button"
					onclick={() => fetchKeys(currentPage)}
					class="mt-3 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
				>
					Retry
				</button>
			</div>
		{:else if items.length === 0}
			<div class="px-4 py-8 text-center">
				<IconKeyVariant class="mx-auto mb-2 h-8 w-8 text-gray-400 dark:text-gray-500" />
				<p class="text-sm font-medium text-gray-900 dark:text-white">No API keys yet</p>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					Create an API key to upload or browse from external scripts and tools.
				</p>
				<button
					type="button"
					onclick={openCreateForm}
					disabled={isCreateOpen}
					class="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
				>
					<IconPlus class="h-3.5 w-3.5" />
					Create your first API key
				</button>
			</div>
		{:else}
			<div class="overflow-x-auto {isLoading ? 'opacity-60 transition-opacity' : ''}">
				<table class="w-full border-collapse text-left text-sm">
					<thead class="hidden border-b border-gray-200 dark:border-gray-700 sm:table-header-group">
						<tr
							class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400"
						>
							<th class="px-4 py-2.5">Name</th>
							<th class="px-3 py-2.5">Prefix</th>
							<th class="px-3 py-2.5">Expires</th>
							<th class="px-4 py-2.5 text-right">Action</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
						{#each items as key (key.id)}
							{@const expired = isExpired(key)}
							{@const isNewlyCreated = createdKey?.id === key.id}
							<tr
								class="block px-4 py-3 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/60 sm:table-row sm:p-0 {isNewlyCreated
									? 'bg-primary-50/70 dark:bg-primary-900/15'
									: ''}"
							>
								<td class="block pb-2 sm:table-cell sm:px-4 sm:py-3">
									<div class="flex items-center gap-2">
										<span class="font-medium text-gray-900 dark:text-white">{key.name}</span>
										{#if isNewlyCreated}
											<span
												class="rounded-full bg-primary-600 px-1.5 py-0.5 text-[10px] font-semibold text-white dark:bg-primary-500"
											>
												New
											</span>
										{/if}
									</div>
									<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
										Last used: {formatLastUsed(key.last_used_at)}
									</div>
								</td>

								<td class="flex items-center justify-between py-1 sm:table-cell sm:px-3 sm:py-3">
									<span
										class="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 sm:hidden"
									>
										Prefix
									</span>
									<code
										class="rounded border border-gray-200 bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
									>
										{key.key_prefix}...
									</code>
								</td>

								<td class="flex items-center justify-between py-1 sm:table-cell sm:px-3 sm:py-3">
									<span
										class="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 sm:hidden"
									>
										Expires
									</span>
									{#if !key.expires_at}
										<span
											class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400"
										>
											Never
										</span>
									{:else if expired}
										<span
											class="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400"
										>
											Expired · {formatDate(key.expires_at)}
										</span>
									{:else}
										<span class="whitespace-nowrap text-xs text-gray-700 dark:text-gray-300">
											{formatDate(key.expires_at)}
										</span>
									{/if}
								</td>

								<td
									class="flex items-center justify-between pt-2 sm:table-cell sm:px-4 sm:py-3 sm:text-right"
								>
									<span
										class="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 sm:hidden"
									>
										Action
									</span>
									{#if confirmingDeleteId === key.id}
										<div class="inline-flex items-center gap-1.5">
											<button
												type="button"
												onclick={() => (confirmingDeleteId = null)}
												disabled={deletingId === key.id}
												class="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
											>
												Cancel
											</button>
											<button
												type="button"
												onclick={() => handleConfirmDelete(key.id)}
												disabled={deletingId === key.id}
												class="rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50 dark:bg-red-500 dark:hover:bg-red-600"
											>
												{deletingId === key.id ? 'Deleting...' : 'Delete'}
											</button>
										</div>
									{:else}
										<button
											type="button"
											onclick={() => {
												actionError = null;
												confirmingDeleteId = key.id;
											}}
											disabled={deletingId !== null}
											class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-gray-500 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:text-gray-400 dark:hover:bg-red-900/20 dark:hover:text-red-400"
											aria-label={`Delete API key ${key.name}`}
										>
											<IconDeleteOutline class="h-4 w-4" />
											Delete
										</button>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			{#if totalPages > 1}
				<nav
					aria-label="API keys pagination"
					class="flex flex-wrap items-center justify-between gap-2 border-t border-gray-200 px-4 py-3 dark:border-gray-700"
				>
					<span class="text-xs text-gray-500 dark:text-gray-400">
						Showing {rangeStart}–{rangeEnd} of {total} keys
					</span>

					<div class="inline-flex items-center gap-1">
						<button
							type="button"
							onclick={() => goToPage(currentPage - 1)}
							disabled={currentPage <= 1 || isLoading}
							class="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
						>
							Prev
						</button>

						{#each visiblePages as token, idx (token === 'ellipsis' ? `ellipsis-${idx}` : token)}
							{#if token === 'ellipsis'}
								<span class="px-1.5 text-xs text-gray-400 dark:text-gray-500">…</span>
							{:else}
								<button
									type="button"
									onclick={() => goToPage(token)}
									disabled={isLoading}
									aria-current={token === currentPage ? 'page' : undefined}
									class="min-w-7 rounded-md border px-2 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed {token ===
									currentPage
										? 'border-primary-600 bg-primary-600 text-white dark:border-primary-500 dark:bg-primary-500'
										: 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'}"
								>
									{token}
								</button>
							{/if}
						{/each}

						<button
							type="button"
							onclick={() => goToPage(currentPage + 1)}
							disabled={currentPage >= totalPages || isLoading}
							class="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
						>
							Next
						</button>
					</div>
				</nav>
			{/if}
		{/if}
	</div>
</div>
