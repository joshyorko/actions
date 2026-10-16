/** Observe same-origin auth failures without changing request bodies or credentials. */
export const observeBrowserAuthFailures = (onFailure: () => void) => {
    const original = window.fetch;
    const observed: typeof fetch = async (input, init) => {
        const response = await original(input, init);
        if (response.status === 403) {
            const url = new URL(
                typeof input === "string" || input instanceof URL
                    ? input
                    : input.url,
                window.location.href,
            );
            if (
                url.origin === window.location.origin &&
                /^\/(api|oauth2|artifacts)\//.test(url.pathname)
            )
                onFailure();
        }
        return response;
    };
    window.fetch = observed;
    return () => {
        if (window.fetch === observed) window.fetch = original;
    };
};
