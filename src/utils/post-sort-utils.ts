import type { PostSection } from "@utils/post-section-utils.ts";

type SortablePost = {
	slug: string;
	data: {
		published: Date | string;
	};
};

type SectionedSortablePost = SortablePost & {
	data: SortablePost["data"] & {
		section: PostSection;
	};
};

const sectionPriority: Record<PostSection, number> = {
	main: 0,
	prerequisite: 1,
	supplement: 2,
};

export function extractPostNumber(slug: string): number | null {
	const match = slug.match(/-(\d+)$/);
	return match ? Number.parseInt(match[1], 10) : null;
}

export function comparePostsByDateThenSlug(
	a: SortablePost,
	b: SortablePost,
): number {
	const dateDifference =
		new Date(b.data.published).getTime() - new Date(a.data.published).getTime();
	return dateDifference || a.slug.localeCompare(b.slug);
}

export function comparePostsByNumberThenDate(
	a: SortablePost,
	b: SortablePost,
): number {
	const numberA = extractPostNumber(a.slug);
	const numberB = extractPostNumber(b.slug);

	if (numberA !== null && numberB !== null) {
		return numberB - numberA || comparePostsByDateThenSlug(a, b);
	}
	if (numberA !== null) return -1;
	if (numberB !== null) return 1;
	return comparePostsByDateThenSlug(a, b);
}

export function comparePostsBySectionThenNumberThenDate(
	a: SectionedSortablePost,
	b: SectionedSortablePost,
): number {
	return (
		sectionPriority[a.data.section] - sectionPriority[b.data.section] ||
		comparePostsByNumberThenDate(a, b)
	);
}
