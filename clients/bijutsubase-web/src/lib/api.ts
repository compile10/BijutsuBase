/**
 * API client for BijutsuBase backend
 */

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
	thumbnail_url: string;
	original_url: string;
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

/**
 * Recommend tags based on user input
 * @param query - Partial tag name to search for
 * @param limit - Maximum number of tags to return
 * @returns Array of recommended tag names
 */
export async function getRecommendedTags(query: string, limit: number = 20): Promise<string[]> {
	const response = await fetch(`/api/tags/recommend?query=${encodeURIComponent(query)}&limit=${limit}`);

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
	const response = await fetch(`/api/tags/danbooru-recs?query=${encodeURIComponent(query)}&limit=${limit}`);

	if (!response.ok) {
		throw new Error(`Failed to get Danbooru recommendations: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Search for files by tags with cursor-based pagination
 * @param tags - Space-separated list of tag names
 * @param sort - Sort order (date_desc, date_asc, size_desc, size_asc)
 * @param cursor - Optional pagination cursor for fetching next page
 * @param limit - Number of items to return per page (default: 60)
 * @returns FileSearchResponse with items, next_cursor, and has_more flag
 */
export async function searchFiles(tags: string, sort: string = 'date_desc', cursor?: string, limit: number = 60): Promise<FileSearchResponse> {
	let url = `/api/files/search?tags=${encodeURIComponent(tags)}&sort=${encodeURIComponent(sort)}&limit=${limit}`;
	if (cursor) {
		url += `&cursor=${encodeURIComponent(cursor)}`;
	}
	
	const response = await fetch(url);
	
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
	const response = await fetch(`/api/files/${sha256}`);
	
	if (!response.ok) {
		throw new Error(`Failed to fetch file: ${response.statusText}`);
	}
	
	return response.json();
}

/**
 * Delete a file by SHA256 hash
 * @param sha256 - SHA256 hash of the file
 * @returns File details prior to deletion
 */
export async function deleteFile(sha256: string): Promise<FileResponse> {
	const response = await fetch(`/api/files/${sha256}`, {
		method: 'DELETE'
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
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request)
	});

	if (!response.ok) {
		throw new Error(`Failed to bulk dissociate tag: ${response.statusText}`);
	}
}
