<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import favicon from '$lib/assets/favicon.svg';
	import UploadModal from '$lib/components/UploadModal.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import { getAppState } from '$lib/state.svelte';
	import { createAuthContext } from '$lib/auth.svelte';
	import { initAuth } from '$lib/api';

	let { children } = $props();
	const appState = getAppState();
	// Create auth context - this provides auth state to all child components
	const authState = createAuthContext();

	// Pages that don't require authentication
	const publicPaths = ['/login', '/setup'];

	function isPublicPath(pathname: string): boolean {
		return publicPaths.some(path => pathname.startsWith(path));
	}

	// Initialize auth on mount
	$effect(() => {
		initAuth();
	});

	// Redirect to setup page if needed (but not if already on setup page)
	$effect(() => {
		if (!authState.isLoading && authState.needsSetup && !page.url.pathname.startsWith('/setup')) {
			goto('/setup');
		}
	});

	// Redirect to login page if not authenticated (unless on a public page)
	$effect(() => {
		if (!authState.isLoading && !authState.needsSetup && !authState.isAuthenticated && !isPublicPath(page.url.pathname)) {
			goto('/login');
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="min-h-screen">
	<!-- Sidebar -->
	<Sidebar bind:isOpen={appState.isSidebarOpen} />

	<!-- Upload Modal -->
	<UploadModal bind:isOpen={appState.isUploadModalOpen} />

	<!-- Loading State -->
	{#if authState.isLoading}
		<div class="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
			<div class="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent"></div>
		</div>
	{:else}
		{@render children()}
	{/if}
</div>
