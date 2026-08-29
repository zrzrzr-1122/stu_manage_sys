import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "Login",
      component: () => import("@/views/Login.vue"),
    },
    {
      path: "/",
      component: () => import("@/views/Layout.vue"),
      redirect: "/home",
      children: [
        { path: "home", name: "Home", component: () => import("@/views/Home.vue") },
        { path: "profile", name: "Profile", component: () => import("@/views/Profile.vue") },
        { path: "scores", name: "Scores", component: () => import("@/views/Scores.vue") },
        { path: "employment", name: "Employment", component: () => import("@/views/Employment.vue") },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const token = localStorage.getItem("portal_token");
  if (to.path !== "/login" && !token) {
    return "/login";
  }
  if (to.path === "/login" && token) {
    return "/home";
  }
  return true;
});

export default router;
