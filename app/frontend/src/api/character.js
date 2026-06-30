export const characterApi = {
  savePreference: async (payload) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ success: true, data: payload });
      }, 500);
    });
  }
};
