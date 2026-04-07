package main

import (
    "internal/services"
)

var Version = "1.0"

func main() {
    services.GetUser(1)
}
