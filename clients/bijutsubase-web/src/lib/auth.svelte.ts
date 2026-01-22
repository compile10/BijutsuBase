/**
 * Authentication state management using Svelte 5 Runes with Context API
 * 
 * This module provides SSR-safe auth state by using Svelte's context API.
 * The auth state is created per-request and attached to the component tree,
 * preventing state leakage between users during server-side rendering.
 */

import { setContext, getContext } from 'svelte';

export interface User {
	id: string;
	email: string;
	is_active: boolean;
	is_superuser: boolean;
	is_verified: boolean;
}

export interface SetupStatus {
	needs_setup: boolean;
}

export interface AuthState {
	token: string | null;
	user: User | null;
	isLoading: boolean;
	needsSetup: boolean;
	readonly isAuthenticated: boolean;
}

// Token storage key
const TOKEN_KEY = 'bijutsubase_token';

// Context key for auth state
const AUTH_CONTEXT_KEY = Symbol('auth');

// Reference to current auth state (for use by api.ts functions)
let currentAuthState: AuthState | null = null;

/**
 * Create the auth context and provide it to child components.
 * Call this in the root +layout.svelte.
 */
export function createAuthContext(): AuthState {
	// Initialize token from localStorage (client-side only)
	let initialToken: string | null = null;
	if (typeof window !== 'undefined') {
		initialToken = localStorage.getItem(TOKEN_KEY);
	}

	// Create reactive state with computed isAuthenticated
	const authState: AuthState = $state({
		token: initialToken,
		user: null as User | null,
		isLoading: true,
		needsSetup: false,
		get isAuthenticated() {
			return this.token !== null && this.user !== null;
		}
	});

	// Store reference for api.ts functions
	currentAuthState = authState;

	// Set context for child components
	setContext(AUTH_CONTEXT_KEY, authState);

	return authState;
}

/**
 * Get the auth state from context.
 * Call this in any component that needs access to auth state.
 */
export function getAuthContext(): AuthState {
	const context = getContext<AuthState | undefined>(AUTH_CONTEXT_KEY);
	if (!context) {
		throw new Error(
			'Auth context not found. Make sure createAuthContext() is called in a parent layout.'
		);
	}
	return context;
}

/**
 * Get the current auth token, or null if not authenticated.
 */
export function getToken(): string | null {
	return currentAuthState?.token ?? null;
}

/**
 * Get authorization headers for API requests.
 * Uses the current auth state reference.
 */
export function getAuthHeaders(): HeadersInit {
	const token = getToken();
	if (token) {
		return {
			Authorization: `Bearer ${token}`
		};
	}
	return {};
}

/**
 * Set the authentication token.
 * Updates both the state and localStorage.
 */
export function setToken(newToken: string) {
	if (currentAuthState) {
		currentAuthState.token = newToken;
	}
	if (typeof window !== 'undefined') {
		localStorage.setItem(TOKEN_KEY, newToken);
	}
}

/**
 * Clear the authentication token.
 * Removes from both state and localStorage.
 */
export function clearToken() {
	if (currentAuthState) {
		currentAuthState.token = null;
		currentAuthState.user = null;
	}
	if (typeof window !== 'undefined') {
		localStorage.removeItem(TOKEN_KEY);
	}
}

/**
 * Set the current user.
 */
export function setUser(newUser: User | null) {
	if (currentAuthState) {
		currentAuthState.user = newUser;
	}
}

/**
 * Set loading state.
 */
export function setLoading(loading: boolean) {
	if (currentAuthState) {
		currentAuthState.isLoading = loading;
	}
}

/**
 * Set needs setup state.
 */
export function setNeedsSetup(needs: boolean) {
	if (currentAuthState) {
		currentAuthState.needsSetup = needs;
	}
}
