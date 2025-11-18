/**
 * API client for BijutsuBase backend
 */

export interface FileThumb {
	sha256_hash: string;
	thumbnail_url: string;
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

/**
 * Search for files by tags
 * @param tags - Space-separated list of tag names
 * @returns Array of file thumbnails
 */
export async function searchFiles(tags: string): Promise<FileThumb[]> {
	const response = await fetch(`/api/files/search?tags=${encodeURIComponent(tags)}`);
	
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

