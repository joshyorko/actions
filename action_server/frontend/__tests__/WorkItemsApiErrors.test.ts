import { describe, expect, it } from "vitest";
import { parseWorkItemsApiError } from "../src/queries/workItems";

function apiResponse(
    body: unknown,
    status: number,
    statusText: string,
): { json: () => Promise<unknown>; status: number; statusText: string } {
    return { json: async () => body, status, statusText };
}

describe("Work Items API error details", () => {
    it("reads the Runtime's assembled HTTP error envelope", async () => {
        const response = apiResponse(
            {
                error_code: "internal-error",
                message:
                    "{'code': 'work_items_storage_unavailable', 'message': 'Work Items could not access local Runtime storage.'}",
                detail: {
                    code: "work_items_storage_unavailable",
                    message:
                        "Work Items could not access local Runtime storage.",
                },
            },
            503,
            "Service Unavailable",
        );

        const error = await parseWorkItemsApiError(response);

        expect(error.status).toBe(503);
        expect(error.code).toBe("work_items_storage_unavailable");
        expect(error.message).toBe(
            "Work Items could not access local Runtime storage.",
        );
    });

    it("preserves the bounded Runtime error code and message", async () => {
        const response = apiResponse(
            {
                detail: {
                    code: "work_items_load_failed",
                    message: "The Runtime could not load Work Items support.",
                },
            },
            503,
            "Service Unavailable",
        );

        const error = await parseWorkItemsApiError(response);

        expect(error.status).toBe(503);
        expect(error.code).toBe("work_items_load_failed");
        expect(error.message).toBe(
            "The Runtime could not load Work Items support.",
        );
    });

    it("retains authorization status for a separate access-denied state", async () => {
        const response = apiResponse({ detail: "Forbidden" }, 403, "Forbidden");

        const error = await parseWorkItemsApiError(response);

        expect(error.status).toBe(403);
        expect(error.code).toBeUndefined();
        expect(error.message).toBe("Forbidden");
    });

    it("falls back to HTTP status text when a server error body is not JSON", async () => {
        const response = {
            status: 500,
            statusText: "Internal Server Error",
            json: async () => {
                throw new Error("not json");
            },
        };

        const error = await parseWorkItemsApiError(response);

        expect(error.status).toBe(500);
        expect(error.message).toBe("Internal Server Error");
    });
});
