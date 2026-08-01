export type PostSection = "main" | "prerequisite" | "supplement";

const sectionLabels: Record<PostSection, string> = {
	main: "主线课程",
	prerequisite: "前置知识",
	supplement: "补充内容",
};

export function getPostSectionLabel(section: PostSection): string {
	return sectionLabels[section];
}
