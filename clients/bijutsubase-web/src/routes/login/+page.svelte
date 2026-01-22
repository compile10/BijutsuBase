<script lang="ts">
	import { goto } from '$app/navigation';
	import { login } from '$lib/api';
	import { getAuthContext } from '$lib/auth.svelte';
	import IconEmail from '~icons/mdi/email';
	import IconLock from '~icons/mdi/lock';
	import IconKey from '~icons/mdi/key';

	const authState = getAuthContext();

	let email = $state('');
	let password = $state('');
	let isLoading = $state(false);
	let error = $state('');

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = '';

		if (!email.trim()) {
			error = 'Email is required';
			return;
		}

		if (!password) {
			error = 'Password is required';
			return;
		}

		isLoading = true;

		try {
			await login(email.trim(), password);
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Login failed';
		} finally {
			isLoading = false;
		}
	}

	// Redirect if already authenticated
	$effect(() => {
		if (!authState.isLoading && authState.isAuthenticated) {
			goto('/');
		}
	});
</script>

<svelte:head>
	<title>Sign In - BijutsuBase</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-10 dark:bg-gray-900">
	<div class="w-full max-w-md">
		<!-- Logo and Title -->
		<div class="mb-8 text-center">
			<div
				class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-600/10 ring-1 ring-primary-600/30 dark:bg-primary-500/10 dark:ring-primary-500/30"
			>
				<IconKey class="h-8 w-8 text-primary-600 dark:text-primary-400" />
			</div>
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white">Welcome back</h1>
			<p class="mt-2 text-gray-600 dark:text-gray-400">Sign in to access your collection</p>
		</div>

		<!-- Login Form -->
		<div class="rounded-2xl bg-white p-8 shadow-xl ring-1 ring-black/5 dark:bg-gray-800 dark:ring-white/10">
			<form onsubmit={handleSubmit} class="space-y-6">
				{#if error}
					<div
						class="rounded-lg bg-red-50 p-4 text-center text-sm text-red-700 ring-1 ring-red-200 dark:bg-red-500/10 dark:text-red-200 dark:ring-red-500/20"
					>
						{error}
					</div>
				{/if}

				<div>
					<label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-200">
						Email Address
					</label>
					<div class="relative mt-2">
						<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
							<IconEmail class="h-5 w-5 text-gray-400 dark:text-gray-500" />
						</div>
						<input
							type="email"
							id="email"
							bind:value={email}
							required
							autocomplete="email"
							class="block w-full rounded-lg border border-gray-300 bg-white py-3 pl-10 pr-4 text-gray-900 placeholder-gray-500 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
							placeholder="you@example.com"
						/>
					</div>
				</div>

				<div>
					<label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-200">
						Password
					</label>
					<div class="relative mt-2">
						<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
							<IconLock class="h-5 w-5 text-gray-400 dark:text-gray-500" />
						</div>
						<input
							type="password"
							id="password"
							bind:value={password}
							required
							autocomplete="current-password"
							class="block w-full rounded-lg border border-gray-300 bg-white py-3 pl-10 pr-4 text-gray-900 placeholder-gray-500 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
							placeholder="Your password"
						/>
					</div>
				</div>

				<button
					type="submit"
					disabled={isLoading}
					class="w-full rounded-lg bg-primary-600 px-4 py-3 font-semibold text-white transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600 dark:focus:ring-primary-400 dark:focus:ring-offset-gray-900"
				>
					{isLoading ? 'Signing in...' : 'Sign In'}
				</button>
			</form>
		</div>
	</div>
</div>
