<template>
  <v-card rounded="lg" class="pa-6">
    <div class="text-h6 mb-4">个人信息</div>
    <v-alert type="info" variant="tonal" class="mb-4">学生端仅支持查看，如需修改请联系教导处。</v-alert>
    <v-row>
      <v-col cols="12" md="6"><v-text-field label="学号" :model-value="form.stu_id" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field label="姓名" :model-value="form.stu_name" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field label="班级ID" :model-value="form.class_id" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field label="学历" :model-value="form.education" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field :model-value="form.major" label="专业" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field :model-value="form.graduateSchool" label="毕业学校" disabled /></v-col>
      <v-col cols="12"><v-text-field :model-value="form.address" label="籍贯" disabled /></v-col>
    </v-row>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, reactive } from "vue";
import http from "@/api/http";

const form = reactive<Record<string, any>>({});

onMounted(async () => {
  Object.assign(form, await http.get("/me"));
});
</script>
