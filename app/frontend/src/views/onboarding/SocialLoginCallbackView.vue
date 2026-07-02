<script setup>
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { userApi } from "../../api/user.js";

const route = useRoute();
const router = useRouter();

onMounted(async () => {
  const provider = route.params.provider;
  const code = route.query.code || "";
  const state = route.query.state || "";
  const providerError = route.query.error || "";

  if (providerError) {
    router.replace("/login");
    return;
  }

  if (!code || !state) {
    router.replace("/login");
    return;
  }

  try {
    const user = await userApi.completeSocialLogin(provider, { code, state });
    localStorage.setItem("binteumsaiLoginBypassed", provider);
    window.dispatchEvent(new CustomEvent("binteumsai-auth-changed", { detail: { user } }));
    router.replace(user.next_path || (user.onboarding_required ? "/onboarding/character" : "/home"));
  } catch (error) {
    router.replace("/login");
  }
});
</script>

<template>
  <section class="callback-view" aria-busy="true" aria-live="polite"></section>
</template>

<style scoped>
.callback-view {
  width: 0;
  height: 0;
  overflow: hidden;
}
</style>
