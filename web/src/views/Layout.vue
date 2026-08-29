<template>
  <div>
    <v-app-bar color="primary" density="comfortable">
      <v-app-bar-title>沃林学生门户</v-app-bar-title>
      <v-spacer />
      <span class="mr-4">{{ name }}</span>
      <v-btn variant="text" @click="logout">退出</v-btn>
    </v-app-bar>

    <v-navigation-drawer permanent>
      <v-list nav>
        <v-list-item to="/home" prepend-icon="mdi-home" title="我的首页" />
        <v-list-item to="/profile" prepend-icon="mdi-account" title="个人信息" />
        <v-list-item to="/scores" prepend-icon="mdi-chart-box" title="我的成绩" />
        <v-list-item to="/employment" prepend-icon="mdi-briefcase" title="就业信息" />
      </v-list>
    </v-navigation-drawer>

    <v-main class="bg-background">
      <v-container class="py-6">
        <router-view />
      </v-container>
    </v-main>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const name = computed(() => localStorage.getItem("portal_name") || "同学");

function logout() {
  localStorage.removeItem("portal_token");
  localStorage.removeItem("portal_name");
  router.push("/login");
}
</script>
