export const userApi = {
  saveProfile: async (payload) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          nickname: payload.nickname,
          age: payload.age,
          gender: payload.gender,
          birth_date: payload.birth_date,
          hobbies: payload.hobbies,
          interests: payload.interests
        });
      }, 500);
    });
  }
};
