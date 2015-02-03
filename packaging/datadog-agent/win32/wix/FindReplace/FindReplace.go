package main

import (
	"fmt"
	"os"
	"strings"

	"io/ioutil"
)

func check(e error) {
	if e != nil {
		panic(e)
		os.Exit(1)
	}
	
}

func main() {
	args := os.Args

	if len(args) != 4 {
		fmt.Println("Usage: FindReplace.exe path_to_file search_text replace_text\n")
		os.Exit(0)
	}

	filePath := args[1]
	searchText := args[2]
	replaceText := args[3]

	if strings.Trim(replaceText, " ") == "" {
		fmt.Println("Replace text can't be empty")
		os.Exit(0)
	}

	parts := strings.Split(replaceText, ":")
	if len(parts) == 2 && strings.Trim(parts[1], " ") == "" {
		fmt.Println("You can't specify an empty key.")
		os.Exit(0)
	}

	contents, err := ioutil.ReadFile(filePath)
	check(err)
	contentsString := string(contents)
	newContents := strings.Replace(contentsString, searchText, replaceText, -1)
	newContentsByte := []byte(newContents)
	err = ioutil.WriteFile(filePath, newContentsByte, 0644)
	check(err)
	os.Exit(0)

}
