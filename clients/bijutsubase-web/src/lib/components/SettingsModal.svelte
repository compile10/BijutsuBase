<script lang="ts">
	import WindowModal from './WindowModal.svelte';
	import { getSettingsContext, type MaxRating } from '$lib/settings.svelte';
	import { getAuthContext } from '$lib/auth.svelte';
	import { updateUser } from '$lib/api';
	import IconClose from '~icons/mdi/close';

	let { isOpen = $bindable(false) }: { isOpen?: boolean } = $props();

	const settings = getSettingsContext();
	const authState = getAuthContext();

	// Avatar state
	let avatarInput = $state(authState.user?.avatar ?? '');
	let avatarError = $state('');
	let avatarSaving = $state(false);

	// Helper to construct avatar URL from sha256 hash
	function getAvatarUrl(sha256: string): string {
		const first2 = sha256.slice(0, 2);
		const next2 = sha256.slice(2, 4);
		return `/media/thumb/${first2}/${next2}/${sha256}.webp`;
	}

	// Check if the avatar input is a valid sha256 hash
	function isValidSha256(hash: string): boolean {
		return /^[a-fA-F0-9]{64}$/.test(hash);
	}

	async function handleAvatarSave() {
		avatarError = '';
		
		// Validate input if not empty
		if (avatarInput && !isValidSha256(avatarInput)) {
			avatarError = 'Invalid SHA256 hash. Must be 64 hexadecimal characters.';
			return;
		}

		avatarSaving = true;
		try {
			await updateUser({ avatar: avatarInput || null });
		} catch (err) {
			avatarError = err instanceof Error ? err.message : 'Failed to update avatar';
		} finally {
			avatarSaving = false;
		}
	}

	async function handleAvatarClear() {
		avatarInput = '';
		avatarError = '';
		avatarSaving = true;
		try {
			await updateUser({ avatar: null });
		} catch (err) {
			avatarError = err instanceof Error ? err.message : 'Failed to clear avatar';
		} finally {
			avatarSaving = false;
		}
	}

	const ratingOptions: { value: MaxRating; label: string; description: string }[] = [
		{
			value: 'safe',
			label: 'Safe',
			description: 'Show only safe content'
		},
		{
			value: 'sensitive',
			label: 'Sensitive',
			description: 'Show safe and sensitive content'
		},
		{
			value: 'questionable',
			label: 'Questionable',
			description: 'Show safe, sensitive, and questionable content'
		},
		{
			value: null,
			label: 'All (including Explicit)',
			description: 'Show all content without filtering'
		}
	];

	function handleRatingChange(value: MaxRating) {
		settings.setMaxRating(value);
	}

	function handleClose() {
		isOpen = false;
	}
</script>

<WindowModal bind:isOpen title="Settings" maxWidth="max-w-3xl" onClose={handleClose}>
	<!-- Header -->
	<div
		class="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700"
	>
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Settings</h2>
		<button
			onclick={handleClose}
			class="rounded-lg p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
			aria-label="Close settings"
		>
			<IconClose class="h-6 w-6" />
		</button>
	</div>

	<!-- Content -->
	<div class="overflow-y-auto px-6 py-6">
		<!-- Account Section -->
		{#if authState.isAuthenticated && authState.user}
			<div class="mb-8">
				<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Account</h3>

				<!-- Avatar Setting -->
				<div class="space-y-3">
					<div class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Avatar
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Set your avatar by entering the SHA256 hash of an uploaded image.
					</p>

					<div class="flex items-start gap-4">
						<!-- Avatar Preview -->
						<div class="shrink-0">
							{#if authState.user.avatar}
								<img
									src={getAvatarUrl(authState.user.avatar)}
									alt="Current avatar"
									class="h-16 w-16 rounded-full object-cover ring-2 ring-gray-200 dark:ring-gray-700"
								/>
							{:else}
								<div class="flex h-16 w-16 items-center justify-center rounded-full bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
									<span class="text-2xl">?</span>
								</div>
							{/if}
						</div>

						<!-- Avatar Input -->
						<div class="flex-1 space-y-2">
							<input
								type="text"
								bind:value={avatarInput}
								placeholder="Enter SHA256 hash (64 hex characters)"
								class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500 dark:focus:border-primary-400 dark:focus:ring-primary-400"
							/>
							{#if avatarError}
								<p class="text-sm text-red-600 dark:text-red-400">{avatarError}</p>
							{/if}
							<div class="flex gap-2">
								<button
									onclick={handleAvatarSave}
									disabled={avatarSaving || avatarInput === (authState.user.avatar ?? '')}
									class="rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
								>
									{avatarSaving ? 'Saving...' : 'Save'}
								</button>
								{#if authState.user.avatar}
									<button
										onclick={handleAvatarClear}
										disabled={avatarSaving}
										class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
									>
										Clear
									</button>
								{/if}
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}

		<!-- General Section -->
		<div class="mb-8">
			<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">General</h3>

			<!-- Rating Filter -->
			<div class="space-y-3">
				<div class="block text-sm font-medium text-gray-700 dark:text-gray-300">
					Content Rating Filter
				</div>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					Control the maximum rating level of content shown. This affects all
					results across the application.
				</p>

				<div class="space-y-2">
					{#each ratingOptions as option (option.value ?? 'null')}
						<button
							onclick={() => handleRatingChange(option.value)}
							class="flex w-full items-start gap-3 rounded-lg border p-4 text-left transition-all {settings.maxRating ===
							option.value
								? 'border-primary-500 bg-primary-50 dark:border-primary-400 dark:bg-primary-900/20'
								: 'border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600'}"
						>
							<div
								class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 {settings.maxRating ===
								option.value
									? 'border-primary-500 dark:border-primary-400'
									: 'border-gray-300 dark:border-gray-600'}"
							>
								{#if settings.maxRating === option.value}
									<div
										class="h-2.5 w-2.5 rounded-full bg-primary-500 dark:bg-primary-400"
									></div>
								{/if}
							</div>
							<div class="flex-1">
								<div
									class="font-medium {settings.maxRating === option.value
										? 'text-primary-900 dark:text-primary-100'
										: 'text-gray-900 dark:text-white'}"
								>
									{option.label}
								</div>
								<div
									class="text-sm {settings.maxRating === option.value
										? 'text-primary-700 dark:text-primary-300'
										: 'text-gray-600 dark:text-gray-400'}"
								>
									{option.description}
								</div>
							</div>
						</button>
					{/each}
				</div>
			</div>
		</div>
	</div>

	<!-- Footer -->
	<div
		class="flex items-center justify-end border-t border-gray-200 px-6 py-4 dark:border-gray-700"
	>
		<button
			onclick={handleClose}
			class="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600"
		>
			Done
		</button>
	</div>
</WindowModal>
