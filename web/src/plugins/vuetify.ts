import "vuetify/styles";
import "@mdi/font/css/materialdesignicons.css";
import { createVuetify } from "vuetify";
import { zhHans } from "vuetify/locale";

export default createVuetify({
  locale: {
    locale: "zhHans",
    messages: { zhHans },
  },
  theme: {
    defaultTheme: "portal",
    themes: {
      portal: {
        dark: false,
        colors: {
          primary: "#165DFF",
          secondary: "#00B42A",
          background: "#F4F6FB",
          surface: "#FFFFFF",
        },
      },
    },
  },
});
