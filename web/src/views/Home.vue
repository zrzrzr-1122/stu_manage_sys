<template>
  <div>
    <div class="text-h5 font-weight-bold mb-2">你好，{{ profile.stu_name || "同学" }}</div>
    <div class="text-medium-emphasis mb-6">这里可以查看个人信息、考试成绩和就业进展。</div>
    <v-row>
      <v-col cols="12" md="4">
        <v-card rounded="lg" class="pa-4">
          <div class="text-subtitle-2 text-medium-emphasis">班级</div>
          <div class="text-h6">{{ profile.class_id ?? "-" }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card rounded="lg" class="pa-4">
          <div class="text-subtitle-2 text-medium-emphasis">学历 / 专业</div>
          <div class="text-h6">{{ profile.education || "-" }} / {{ profile.major || "-" }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card rounded="lg" class="pa-4">
          <div class="text-subtitle-2 text-medium-emphasis">成绩条数</div>
          <div class="text-h6">{{ scores.length }}</div>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "@/api/http";

const profile = ref<Record<string, any>>({});
const scores = ref<any[]>([]);

onMounted(async () => {
  profile.value = (await http.get("/me")) || {};
  scores.value = (await http.get("/scores")) || [];
  if (profile.value.stu_name) {
    localStorage.setItem("portal_name", profile.value.stu_name);
  }
});
</script>
