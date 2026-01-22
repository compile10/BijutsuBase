/**
 * API client for BijutsuBase backend
 */

import { getAuthHeaders, getToken, setToken, clearToken, setUser, setLoading, setNeedsSetup, type User, type SetupStatus } from './auth.svelte';

export class APIError extends Error {
	status: number;
	statusText: string;

	constructor(response: Response, message?: string) {
		super(message ?? `Request failed with status ${response.status} ${response.statusText}`);
		this.name = 'APIError';
		this.status = response.status;
		this.statusText = response.statusText;
	}
}

// Re-export User type for convenience
export type { User, SetupStatus };

/**
 * Login response from the API
 */
export interface LoginResponse {
	access_token: string;
	token_type: string;
}

/**
 * Check if the application needs initial setup
 */
export async function checkSetupStatus(): Promise<SetupStatus> {
	const response = await fetch('/api/setup/status');
	
	if (!response.ok) {
		throw new APIError(response, 'Failed to check setup status');
	}
	
	return response.json();
}

/**
 * Create the initial admin account
 */
export async function createAdminAccount(email: string, password: string): Promise<{ success: boolean; message: string }> {
	const response = await fetch('/api/setup/admin', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password })
	});
	
	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Failed to create admin account' }));
		throw new APIError(response, error.detail || 'Failed to create admin account');
	}
	
	return response.json();
}

/**
 * Login with email and password
 */
export async function login(email: string, password: string): Promise<LoginResponse> {
	// FastAPI Users expects form data for login
	const formData = new URLSearchParams();
	formData.append('username', email);
	formData.append('password', password);
	
	const response = await fetch('/api/auth/jwt/login', {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body: formData
	});
	
	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Login failed' }));
		throw new APIError(response, error.detail || 'Login failed');
	}
	
	const data: LoginResponse = await response.json();
	setToken(data.access_token);
	
	// Fetch user info after login
	await getCurrentUser();
	
	return data;
}

/**
 * Logout the current user
 */
export async function logout(): Promise<void> {
	try {
		await fetch('/api/auth/jwt/logout', {
			method: 'POST',
			headers: getAuthHeaders()
		});
	} catch {
		// Ignore errors during logout
	}
	
	clearToken();
}

/**
 * Get the current authenticated user
 */
export async function getCurrentUser(): Promise<User | null> {
	if (!getToken()) {
		setUser(null);
		return null;
	}
	
	const response = await fetch('/api/users/me', {
		headers: getAuthHeaders()
	});
	
	if (!response.ok) {
		if (response.status === 401) {
			clearToken();
			setUser(null);
			return null;
		}
		throw new APIError(response, 'Failed to get current user');
	}
	
	const user: User = await response.json();
	setUser(user);
	return user;
}

/**
 * Initialize authentication state
 * Checks setup status and validates current token
 */
export async function initAuth(): Promise<void> {
	setLoading(true);
	
	try {
		// Check if setup is needed
		const status = await checkSetupStatus();
		setNeedsSetup(status.needs_setup);
		
		if (!status.needs_setup) {
			// Try to get current user (validates token)
			await getCurrentUser();
		}
	} catch (error) {
		console.error('Failed to initialize auth:', error);
	} finally {
		setLoading(false);
	}
}

export interface FileThumb {
	sha256_hash: string;
	thumbnail_url: string;
}

export interface FileSearchResponse {
	items: FileThumb[];
	next_cursor: string | null;
	has_more: boolean;
}

export interface TagResponse {
	name: string;
	category: string;
	count: number;
}

export type TagCategory = 'general' | 'artist' | 'copyright' | 'character' | 'meta';

export interface FileResponse {
	sha256_hash: string;
	md5_hash: string;
	file_size: number;
	original_filename: string;
	file_ext: string;
	file_type: string;
	width: number | null;
	height: number | null;
	rating: string;
	date_added: string;
	source: string | null;
	ai_generated: boolean;
	tag_source: string;
	tags: TagResponse[];
	pools: PoolSimple[];
	parent?: FileThumb | null;
	children?: FileThumb[];
	family_id?: string | null;
	thumbnail_url: string;
	original_url: string;
}

export interface FileFamilyResponse {
	id: string; // UUID
	parent_sha256_hash: string;
	parent: FileThumb | null;
	children: FileThumb[];
	created_at: string;
	updated_at: string;
}

export interface CreateFamilyRequest {
	parent_sha256_hash: string;
}

export interface AddChildRequest {
	child_sha256_hash: string;
}

export interface TagAssociateRequest {
	file_sha256: string;
	tag_name: string;
	category: string;
}

export interface TagDissociateRequest {
	file_sha256: string;
	tag_name: string;
}

export interface BulkFileRequest {
	file_hashes: string[];
}

export interface BulkUpdateFileRequest {
	file_hashes: string[];
	rating?: string;
	ai_generated?: boolean;
}

export interface BulkTagAssociateRequest {
	file_hashes: string[];
	tag_name: string;
	category: string;
}

export interface BulkTagDissociateRequest {
	file_hashes: string[];
	tag_name: string;
}

export interface ReorderFilesRequest {
	file_hashes: string[];
	after_order: number;
}

export enum PoolCategory {
	SERIES = 'series',
	COLLECTION = 'collection'
}

export interface PoolSimple {
	id: string;
	name: string;
	member_count: number;
	thumbnail_url: string | null;
}

export interface CreatePoolRequest {
	name: string;
	description?: string;
	category?: PoolCategory;
}

export interface PoolResponse extends PoolSimple {
	description: string | null;
	category: PoolCategory;
	created_at: string;
	updated_at: string;
	members: PoolMemberResponse[];
}

export interface PoolMemberResponse {
	file: FileThumb;
	order: number;
	added_at: string;
}

export interface TagBrowseItem {
	name: string;
	count: number;
	thumbnail_url: string | null;
}

/**
 * Recommend tags based on user input
 * @param query - Partial tag name to search for
 * @param limit - Maximum number of tags to return
 * @returns Array of recommended tag names
 */
export async function getRecommendedTags(query: string, limit: number = 20): Promise<string[]> {
	const response = await fetch(`/api/tags/recommend?query=${encodeURIComponent(query)}&limit=${limit}`, {
		headers: getAuthHeaders()
	});

	if (!response.ok) {
		throw new Error(`Failed to get recommendations: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Get tag recommendations from Danbooru
 * @param query - Partial tag name to search for
 * @param limit - Maximum number of tags to return
 * @returns Array of Danbooru tag recommendations with mapped categories
 */
export async function getDanbooruRecommendedTags(query: string, limit: number = 20): Promise<TagResponse[]> {
	const response = await fetch(`/api/tags/danbooru-recs?query=${encodeURIComponent(query)}&limit=${limit}`, {
		headers: getAuthHeaders()
	});

	if (!response.ok) {
		throw new Error(`Failed to get Danbooru recommendations: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Search for files by tags with cursor-based pagination
 * @param tags - Space-separated list of tag names
 * @param sort - Sort order (date_desc, date_asc, size_desc, size_asc, random)
 * @param cursor - Optional pagination cursor for fetching next page
 * @param limit - Number of items to return per page (default: 60)
 * @param seed - Optional seed for random sorting
 * @returns FileSearchResponse with items, next_cursor, and has_more flag
 */
export async function searchFiles(tags: string, sort: string = 'date_desc', cursor?: string, limit: number = 100, seed?: string): Promise<FileSearchResponse> {
	let url = `/api/files/search?tags=${encodeURIComponent(tags)}&sort=${encodeURIComponent(sort)}&limit=${limit}`;
	if (cursor) {
		url += `&cursor=${encodeURIComponent(cursor)}`;
	}
	if (seed) {
		url += `&seed=${encodeURIComponent(seed)}`;
	}
	
	const response = await fetch(url, {
		headers: getAuthHeaders()
	});
	
	if (!response.ok) {
		throw new Error(`Search failed: ${response.statusText}`);
	}
	
	return response.json();
}

/**
 * Get file details by SHA256 hash
 * @param sha256 - SHA256 hash of the file
 * @returns File details including tags and URLs
 */
export async function getFile(sha256: string): Promise<FileResponse> {
	const response = await fetch(`/api/files/${sha256}`, {
		headers: getAuthHeaders()
	});
	
	if (!response.ok) {
		throw new APIError(response, `Failed to fetch file: ${response.statusText}`);
	}
	
	return response.json();
}

/**
 * Delete a file by SHA256 hash
 * @param sha256 - SHA256 hash of the file
 * @returns ok response
 */
export async function deleteFile(sha256: string): Promise<{ ok: boolean }> {
	const response = await fetch(`/api/files/${sha256}`, {
		method: 'DELETE',
		headers: getAuthHeaders()
	});
	
	if (!response.ok) {
		throw new Error(`Failed to delete file: ${response.statusText}`);
	}
	
	return response.json();
}

/**
 * Upload a file
 * @param file - File to upload
 * @returns Uploaded file details
 */
export async function uploadFile(file: File): Promise<FileResponse> {
	const formData = new FormData();
	formData.append('file', file);
	
	const response = await fetch('/api/upload/file', {
		method: 'PUT',
		headers: getAuthHeaders(),
		body: formData
	});
	
	if (!response.ok) {
		throw new Error(`Upload failed: ${response.statusText}`);
	}
	
	return response.json();
}

/**
 * Upload by URL
 * @param url - Direct URL to an image or video
 * @returns Uploaded file details
 */
export async function uploadByUrl(url: string): Promise<FileResponse> {
	const response = await fetch('/api/upload/url', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify({ url })
	});

	if (!response.ok) {
		throw new Error(`URL upload failed: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Associate a tag with a file
 * @param request - Request containing file_sha256, tag_name, and category
 * @returns Updated file details with new tag
 */
export async function associateTag(request: TagAssociateRequest): Promise<FileResponse> {
	const response = await fetch('/api/tags/associate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify(request)
	});

	if (!response.ok) {
		throw new Error(`Failed to associate tag: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Dissociate a tag from a file
 * @param request - Request containing file_sha256 and tag_name
 * @returns Updated file details without the removed tag
 */
export async function dissociateTag(request: TagDissociateRequest): Promise<FileResponse> {
	const response = await fetch('/api/tags/dissociate', {
		method: 'DELETE',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify(request)
	});

	if (!response.ok) {
		throw new Error(`Failed to dissociate tag: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Update the rating of a file
 * @param sha256 - SHA256 hash of the file
 * @param rating - New rating value (safe, sensitive, questionable, explicit)
 * @returns Updated file details with new rating
 */
export async function updateFileRating(sha256: string, rating: string): Promise<FileResponse> {
	const response = await fetch(`/api/files/rating/${sha256}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify({ rating })
	});

	if (!response.ok) {
		throw new Error(`Failed to update rating: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Update the ai_generated status of a file
 * @param sha256 - SHA256 hash of the file
 * @param aiGenerated - New ai_generated status
 * @returns Updated file details with new status
 */
export async function updateFileAiGenerated(sha256: string, aiGenerated: boolean): Promise<FileResponse> {
	const response = await fetch(`/api/files/ai_generated/${sha256}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify({ ai_generated: aiGenerated })
	});

	if (!response.ok) {
		throw new Error(`Failed to update ai_generated status: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Get tags common to all specified files
 * @param hashes - List of file SHA256 hashes
 * @returns Array of common tags
 */
export async function getCommonTags(hashes: string[]): Promise<TagResponse[]> {
	const response = await fetch('/api/files/bulk-common-tags', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify({ file_hashes: hashes })
	});

	if (!response.ok) {
		throw new Error(`Failed to fetch common tags: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Bulk update file metadata
 * @param request - Bulk update request
 */
export async function bulkUpdateFileMetadata(request: BulkUpdateFileRequest): Promise<void> {
	const response = await fetch('/api/files/bulk-update', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify(request)
	});

	if (!response.ok) {
		throw new Error(`Failed to bulk update files: ${response.statusText}`);
	}
}

/**
 * Bulk associate tag with files
 * @param request - Bulk tag associate request
 */
export async function bulkAssociateTag(request: BulkTagAssociateRequest): Promise<void> {
	const response = await fetch('/api/tags/bulk-associate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify(request)
	});

	if (!response.ok) {
		throw new Error(`Failed to bulk associate tag: ${response.statusText}`);
	}
}

/**
 * Bulk dissociate tag from files
 * @param request - Bulk tag dissociate request
 */
export async function bulkDissociateTag(request: BulkTagDissociateRequest): Promise<void> {
	const response = await fetch('/api/tags/bulk-dissociate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify(request)
	});

	if (!response.ok) {
		throw new Error(`Failed to bulk dissociate tag: ${response.statusText}`);
	}
}

/**
 * Get list of pools
 * @param skip - Number of items to skip
 * @param limit - Number of items to return
 * @returns Array of pools
 */
export async function getPools(skip: number = 0, limit: number = 50, query?: string): Promise<PoolSimple[]> {
	let url = `/api/pools/?skip=${skip}&limit=${limit}`;
	if (query) {
		url += `&query=${encodeURIComponent(query)}`;
	}
	const response = await fetch(url, {
		headers: getAuthHeaders()
	});

	if (!response.ok) {
		throw new Error(`Failed to fetch pools: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Browse tags by category (alphabetical, paginated)
 * @param skip - Number of items to skip
 * @param limit - Number of items to return
 * @returns Array of tags with example thumbnails
 */
export async function getTagsByCategory(category: TagCategory, skip: number = 0, limit: number = 50): Promise<TagBrowseItem[]> {
	const response = await fetch(
		`/api/tags/browse?category=${encodeURIComponent(category)}&skip=${skip}&limit=${limit}`,
		{
			headers: getAuthHeaders()
		}
	);

	if (!response.ok) {
		throw new Error(`Failed to fetch tags: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Create a new pool
 * @param request - Pool creation request
 * @returns Created pool details
 */
export async function createPool(request: CreatePoolRequest): Promise<PoolResponse> {
	const response = await fetch('/api/pools/', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify(request)
	});

	if (!response.ok) {
		throw new Error(`Failed to create pool: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Fetch full details for a single pool
 * @param id - Pool ID (UUID string)
 */
export async function getPool(id: string): Promise<PoolResponse> {
	const response = await fetch(`/api/pools/${id}`, {
		headers: getAuthHeaders()
	});

	if (!response.ok) {
		throw new Error(`Failed to fetch pool: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Add one or more files to a pool
 * @param poolId - Pool ID (UUID string)
 * @param fileHashes - Array of SHA-256 hashes to add
 */
export async function addFilesToPool(poolId: string, fileHashes: string[]): Promise<PoolResponse> {
	const response = await fetch(`/api/pools/${poolId}/files`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify({
			file_hashes: fileHashes
		} satisfies BulkFileRequest)
	});

	if (!response.ok) {
		throw new Error(`Failed to add files to pool: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Remove a single file from a pool
 * @param poolId - Pool ID (UUID string)
 * @param sha256 - File SHA-256 hash to remove
 */
export async function removeFileFromPool(poolId: string, sha256: string): Promise<PoolResponse> {
	const response = await fetch(`/api/pools/${poolId}/files/${sha256}`, {
		method: 'DELETE',
		headers: getAuthHeaders()
	});

	if (!response.ok) {
		throw new Error(`Failed to remove file from pool: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Create a new family for a parent file
 */
export async function createFamily(parentSha256: string): Promise<FileFamilyResponse> {
	const response = await fetch('/api/families/', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify({
			parent_sha256_hash: parentSha256
		} satisfies CreateFamilyRequest)
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => null);
		const detail = errorData?.detail ?? response.statusText;
		throw new Error(detail);
	}

	return response.json();
}

/**
 * Add a child file to a family
 */
export async function addChildToFamily(familyId: string, childSha256: string): Promise<FileFamilyResponse> {
	const response = await fetch(`/api/families/${familyId}/children`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify({
			child_sha256_hash: childSha256
		} satisfies AddChildRequest)
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => null);
		const detail = errorData?.detail ?? response.statusText;
		throw new Error(detail);
	}

	return response.json();
}

/**
 * Remove a child file from a family
 */
export async function removeChildFromFamily(familyId: string, childSha256: string): Promise<FileFamilyResponse> {
	const response = await fetch(`/api/families/${familyId}/children/${childSha256}`, {
		method: 'DELETE',
		headers: getAuthHeaders()
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => null);
		const detail = errorData?.detail ?? response.statusText;
		throw new Error(detail);
	}

	return response.json();
}

/**
 * Delete a family (unlinks children; does not delete files)
 */
export async function deleteFamily(familyId: string): Promise<void> {
	const response = await fetch(`/api/families/${familyId}`, {
		method: 'DELETE',
		headers: getAuthHeaders()
	});

	// delete returns 204 on success
	if (!response.ok) {
		const errorData = await response.json().catch(() => null);
		const detail = errorData?.detail ?? response.statusText;
		throw new Error(detail);
	}
}

/**
 * Reorder files in a pool
 * @param poolId - Pool ID (UUID string)
 * @param fileHashes - Array of SHA-256 hashes to reorder
 * @param afterOrder - Position after which to insert the files (0-indexed)
 */
export async function reorderPoolFiles(poolId: string, fileHashes: string[], afterOrder: number): Promise<PoolResponse> {
	const response = await fetch(`/api/pools/${poolId}/reorder`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
		body: JSON.stringify({
			file_hashes: fileHashes,
			after_order: afterOrder
		} satisfies ReorderFilesRequest)
	});

	if (!response.ok) {
		throw new Error(`Failed to reorder files in pool: ${response.statusText}`);
	}

	return response.json();
}
