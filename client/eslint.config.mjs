import path from "node:path";
import { fileURLToPath } from "node:url";

import { getTSConfig } from "@thelabnyc/standards/eslint.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default getTSConfig({
    parserOptions: {
        tsconfigRootDir: __dirname,
    },
    configs: [
        {
            ignores: ["postcss.config.js", "webpack.config.js"],
        },
    ],
});
