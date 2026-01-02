"""Automatic family creation based on visual similarity."""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from utils.parent_determination import determine_parent

if TYPE_CHECKING:
    from models.file import File
    from models.family import FileFamily

logger = logging.getLogger(__name__)


async def handle_similar_files(
    new_file: "File",
    similar_files: list[tuple["File", int]],
    db: AsyncSession,
) -> None:
    """
    Handle automatic family creation/extension based on visually similar files.
    
    Logic:
    1. If no similar files: do nothing
    2. If similar files exist but none in families: create new family with best parent
    3. If similar file is in a family: add new file to that family
    4. If multiple similar files in different families: merge families
    
    Args:
        new_file: The newly uploaded file
        similar_files: List of (File, hamming_distance) tuples for similar files
        db: Database session
        
    Note:
        This function commits changes to the database.
    """
    from models.family import FileFamily
    
    if not similar_files:
        logger.debug(f"No similar files found for {new_file.sha256_hash}")
        return
    
    logger.info(
        f"Found {len(similar_files)} similar file(s) for {new_file.sha256_hash} "
        f"(distances: {[d for _, d in similar_files]})"
    )
    
    # Collect all similar files and their family info
    files_with_families: list[tuple["File", "FileFamily | None"]] = []
    
    for similar_file, distance in similar_files:
        # Determine which family this file belongs to
        if similar_file.family_as_parent:
            # This file is a parent of a family
            family = similar_file.family_as_parent
        elif similar_file.parent_family_id:
            # This file is a child in a family
            family = similar_file.family_as_child
        else:
            # This file is not in any family
            family = None
        
        files_with_families.append((similar_file, family))
    
    # Get unique families (excluding None)
    unique_families = {family for _, family in files_with_families if family is not None}
    
    if len(unique_families) == 0:
        # Case 1: No existing families - create new family with best parent
        await _create_new_family_from_similar(new_file, [f for f, _ in files_with_families], db)
    
    elif len(unique_families) == 1:
        # Case 2: All similar files are in the same family - add new file to it
        family = next(iter(unique_families))
        await _add_to_existing_family(new_file, family, db)
    
    else:
        # Case 3: Multiple families - merge them and add new file
        await _merge_families_and_add_file(new_file, list(unique_families), [f for f, _ in files_with_families], db)


async def _create_new_family_from_similar(
    new_file: "File",
    similar_files: list["File"],
    db: AsyncSession,
) -> None:
    """
    Create a new family from a set of similar files (none currently in families).
    
    Determines the best parent using determine_parent() and creates a family with
    all files as children (except the parent).
    """
    from models.family import FileFamily
    
    # Include new file in the set of candidates
    all_files = similar_files + [new_file]
    
    # Determine the best parent from all similar files
    parent = all_files[0]
    for file in all_files[1:]:
        parent = determine_parent(parent, file)
    
    logger.info(
        f"Creating new family with parent {parent.sha256_hash} "
        f"from {len(all_files)} similar files"
    )
    
    # Create the family
    family = FileFamily(parent_sha256_hash=parent.sha256_hash)
    db.add(family)
    await db.flush()  # Get the family ID
    
    # Add all other files as children
    for file in all_files:
        if file.sha256_hash != parent.sha256_hash:
            file.parent_family_id = family.id
     
    await db.commit()
    logger.info(f"Created family {family.id} with {len(all_files) - 1} children")


async def _add_to_existing_family(
    new_file: "File",
    family: "FileFamily",
    db: AsyncSession,
) -> None:
    """
    Add a new file to an existing family.
    
    Checks if the new file should become the parent (better quality) and
    reorganizes the family if needed.
    """
    # Load the current parent with tags for comparison
    result = await db.execute(
        select(family.parent).options(selectinload(family.parent.tags))
    )
    # Accessing the parent relationship which is already loaded
    current_parent = family.parent
    
    # Check if new file should be the parent instead
    best_parent = determine_parent(current_parent, new_file)
    
    if best_parent.sha256_hash == new_file.sha256_hash:
        # New file should be the parent - reorganize family
        logger.info(
            f"New file {new_file.sha256_hash} is better quality than current parent "
            f"{current_parent.sha256_hash}, reorganizing family {family.id}"
        )
        
        # Current parent becomes a child
        current_parent.parent_family_id = family.id
        
        # New file becomes the parent
        family.parent_sha256_hash = new_file.sha256_hash
    else:
        # New file becomes a child
        logger.info(f"Adding new file {new_file.sha256_hash} as child to family {family.id}")
        new_file.parent_family_id = family.id
    
    await db.commit()


async def _merge_families_and_add_file(
    new_file: "File",
    families: list["FileFamily"],
    all_similar_files: list["File"],
    db: AsyncSession,
) -> None:
    """
    Merge multiple families into one and add the new file.
    
    Determines the best parent from all files across all families,
    creates/updates a family with that parent, and moves all files to it.
    """
    logger.info(f"Merging {len(families)} families due to similar file {new_file.sha256_hash}")
    
    # Collect all files from all families (parents and children)
    all_files: set[File] = {new_file}
    
    for family in families:
        if family.parent:
            all_files.add(family.parent)
        all_files.update(family.children)
    
    # Add any standalone similar files not already included
    all_files.update(all_similar_files)
    
    # Determine the best parent from all files
    parent = all_files[0]
    for file in all_files[1:]:
        parent = determine_parent(parent, file)
    
    logger.info(f"Best parent for merged family: {parent.sha256_hash}")
    
    # Find or create the family with this parent
    target_family = None
    for family in families:
        if family.parent_sha256_hash == parent.sha256_hash:
            target_family = family
            break
    
    if target_family is None:
        # Create new family with the chosen parent
        from models.family import FileFamily
        target_family = FileFamily(parent_sha256_hash=parent.sha256_hash)
        db.add(target_family)
        await db.flush()
        logger.info(f"Created new merged family {target_family.id}")
    else:
        logger.info(f"Using existing family {target_family.id} as merge target")
    
    # Move all non-parent files to this family as children
    for file in all_files:
        if file.sha256_hash != parent.sha256_hash:
            file.parent_family_id = target_family.id
    
    # Delete the other families
    for family in families:
        if family.id != target_family.id:
            logger.info(f"Deleting merged family {family.id}")
            await db.delete(family)
    
    await db.commit()
    logger.info(
        f"Merged {len(families)} families into family {target_family.id} "
        f"with {len(all_files) - 1} children"
    )

