package services

import (
    "myapp/internal/types"
    "myapp/internal/config"
)

func GetUser(id int) types.User {
    _ = config.AppName
    return types.User{ID: id, Name: "test"}
}
