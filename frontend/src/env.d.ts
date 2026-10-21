/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DEMO_VK_ID?: string;
  readonly VITE_VK_GROUP_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
