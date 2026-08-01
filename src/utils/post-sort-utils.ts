type SortablePost = {
	slug: string;
	data: {
		published: Date | string;
	};
};

export function extractPostNumber(slug: string): number | null {
	const match = slug.match(/-(\d+)$/);
	return match ? Number.parseInt(match[1], 10) : null;
}

function compareByDateThenSlug(a: SortablePost, b: SortablePost): number {
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
		return numberB - numberA || compareByDateThenSlug(a, b);
	}
	if (numberA !== null) return -1;
	if (numberB !== null) return 1;
	return compareByDateThenSlug(a, b);
}
