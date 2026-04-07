package services

import (
    "internal/types"
    "cmd"
)

func GetUser(id int) types.User {
    _ = cmd.Version
    return types.User{ID: id, Name: "test"}
}
