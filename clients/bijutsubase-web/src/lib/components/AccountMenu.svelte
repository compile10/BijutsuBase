<script lang="ts">
	import { scale } from 'svelte/transition';
	import { goto } from '$app/navigation';
	import { getAuthContext } from '$lib/auth.svelte';
	import { logout } from '$lib/api';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import IconAccount from '~icons/mdi/account-circle';
	import IconLogout from '~icons/mdi/logout';
	import IconLogin from '~icons/mdi/login';
	import IconChevronDown from '~icons/mdi/chevron-down';
	import IconSettings from '~icons/mdi/cog';

	const authState = getAuthContext();
	let isMenuOpen = $state(false);
	let isSettingsOpen = $state(false);
	let menuRef = $state<HTMLDivElement | null>(null);

	// Helper to construct avatar URL from sha256 hash
	function getAvatarUrl(sha256: string): string {
		const first2 = sha256.slice(0, 2);
		const next2 = sha256.slice(2, 4);
		return `/media/thumb/${first2}/${next2}/${sha256}.webp`;
	}

	function toggleMenu() {
		isMenuOpen = !isMenuOpen;
	}

	function closeMenu() {
		isMenuOpen = false;
	}

	function handleSettings() {
		isSettingsOpen = true;
		closeMenu();
	}

	async function handleLogout() {
		await logout();
		closeMenu();
		goto('/login');
	}

	function handleClickOutside(event: MouseEvent) {
		if (menuRef && !menuRef.contains(event.target as Node)) {
			closeMenu();
		}
	}

	$effect(() => {
		if (isMenuOpen) {
			document.addEventListener('click', handleClickOutside);
			return () => {
				document.removeEventListener('click', handleClickOutside);
			};
		}
	});
</script>

<div class="relative" bind:this={menuRef}>
	{#if authState.isAuthenticated && authState.user}
		<!-- Authenticated: Show user menu -->
		<button
			onclick={toggleMenu}
			class="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
			aria-expanded={isMenuOpen}
			aria-haspopup="true"
		>
			{#if authState.user.avatar}
				<img
					src={getAvatarUrl(authState.user.avatar)}
					alt="Avatar"
					class="h-5 w-5 rounded-full object-cover"
				/>
			{:else}
				<IconAccount class="h-5 w-5" />
			{/if}
			<span class="hidden sm:inline max-w-[120px] truncate">{authState.user.username}</span>
			<IconChevronDown class="h-4 w-4 transition-transform {isMenuOpen ? 'rotate-180' : ''}" />
		</button>

		{#if isMenuOpen}
			<div
				class="absolute right-0 top-full z-50 mt-2 w-56 origin-top-right"
				transition:scale={{ duration: 150, start: 0.95 }}
			>
				<div class="rounded-lg bg-white py-1 shadow-lg ring-1 ring-black/5 dark:bg-gray-800 dark:ring-white/10">
					<!-- User info -->
					<div class="border-b border-gray-100 px-4 py-3 dark:border-gray-700">
						<div class="flex items-center gap-3">
							{#if authState.user.avatar}
								<img
									src={getAvatarUrl(authState.user.avatar)}
									alt="Avatar"
									class="h-10 w-10 shrink-0 rounded-full object-cover ring-2 ring-gray-200 dark:ring-gray-700"
								/>
							{:else}
								<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400">
									<IconAccount class="h-6 w-6" />
								</div>
							{/if}
							<div class="min-w-0 flex-1">
								<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
									{authState.user.username}
								</p>
								<p class="text-xs text-gray-500 dark:text-gray-400 truncate">
									{authState.user.email}
								</p>
								{#if authState.user.is_superuser}
									<p class="text-xs text-purple-600 dark:text-purple-400">Administrator</p>
								{/if}
							</div>
						</div>
					</div>

					<!-- Menu items -->
					<div class="py-1">
						<button
							onclick={handleSettings}
							class="flex w-full items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
						>
							<IconSettings class="h-4 w-4" />
							Settings
						</button>
						<button
							onclick={handleLogout}
							class="flex w-full items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
						>
							<IconLogout class="h-4 w-4" />
							Sign out
						</button>
					</div>
				</div>
			</div>
		{/if}
	{:else}
		<!-- Not authenticated: Show login link -->
		<a
			href="/login"
			class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600"
		>
			<IconLogin class="h-4 w-4" />
			<span>Sign In</span>
		</a>
	{/if}
</div>

<SettingsModal bind:isOpen={isSettingsOpen} />
